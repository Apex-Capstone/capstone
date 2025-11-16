"""Scoring service for empathy, communication, and SPIKES metrics."""

import json
from typing import Any

from sqlalchemy.orm import Session

from core.errors import NotFoundError
from domain.entities.feedback import Feedback
from domain.models.sessions import FeedbackResponse
from repositories.feedback_repo import FeedbackRepository
from repositories.session_repo import SessionRepository
from repositories.turn_repo import TurnRepository


class ScoringService:
    """Service for calculating performance scores and feedback."""
    
    def __init__(self, db: Session):
        self.db = db
        self.session_repo = SessionRepository(db)
        self.turn_repo = TurnRepository(db)
        self.feedback_repo = FeedbackRepository(db)
    
    def _parse_metrics_json(self, metrics_json: str) -> dict[str, Any] | None:
        """Parse metrics_json, handling both proper JSON and string representations."""
        if not metrics_json:
            return None
        
        try:
            # Try parsing as proper JSON first (new format)
            return json.loads(metrics_json)
        except json.JSONDecodeError:
            try:
                # Fallback: handle string representation (old format)
                return json.loads(metrics_json.replace("'", '"'))
            except:
                return None
    
    def _deserialize_json_field(self, value: str | None) -> dict | list | None:
        """Deserialize JSON string to dict/list, or return None."""
        if value is None or value == "":
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None
        # If already dict/list, return as-is (shouldn't happen, but safe)
        return value if isinstance(value, (dict, list)) else None

    async def generate_feedback(self, session_id: int) -> FeedbackResponse:
        """Generate comprehensive feedback for a session."""
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise NotFoundError(f"Session {session_id} not found")
        
        turns = self.turn_repo.get_by_session(session_id)
        
        # Extract spans from all turns
        all_spans = self._extract_spans_from_turns(turns)
        
        # Calculate AFCE-structured metrics from spans
        eo_counts_by_dimension = self._calculate_eo_counts_by_dimension(all_spans)
        elicitation_counts_by_type = self._calculate_elicitation_counts_by_type(all_spans)
        response_counts_by_type = self._calculate_response_counts_by_type(all_spans)
        
        # Calculate scores
        empathy_score = self._calculate_empathy_score_from_afce(
            eo_counts_by_dimension, 
            response_counts_by_type,
            all_spans,
            turns
        )
        spikes_score = self._calculate_spikes_completion(session, turns, all_spans)
        overall_score = round((empathy_score + spikes_score) / 2.0, 2)  # Simple average, rounded
        
        # Calculate SPIKES metrics (will update to exclude Setting in Part 2)
        spikes_coverage = self._analyze_spikes_coverage(turns)
        spikes_timestamps = self._calculate_spikes_timestamps(turns)
        spikes_strategies = self._identify_spikes_strategies(turns)
        
        # Calculate questioning metrics
        question_breakdown = self._calculate_question_breakdown(turns)
        
        # Calculate performance metrics
        latency_ms_avg = self._calculate_latency_ms_avg(turns)
        
        # Placeholder fields for fairness/reliability (only include if populated)
        bias_probe_info = None  # Would be populated by bias testing framework
        evaluator_meta = None  # Would be populated by evaluation system
        
        # Collect span lists for feedback generation
        eo_spans, elicitation_spans, response_spans = self._collect_span_lists(all_spans)
        
        # Implement linking logic (Part 2)
        eo_to_response_links, missed_opportunities, linkage_stats = self._compute_eo_linking(
            eo_spans, response_spans, elicitation_spans, turns
        )
        eo_to_elicitation_links = self._compute_eo_to_elicitation_links(
            eo_spans, elicitation_spans, turns
        )
        missed_opportunities_by_dimension = self._compute_missed_opportunities_by_dimension(
            missed_opportunities, eo_spans
        )
        
        # Generate textual feedback
        strengths, improvements = self._generate_textual_feedback(
            empathy_score,
            None,  # communication_score deprecated
            spikes_score,
            question_breakdown,
            eo_spans,
        )
        
        # Create or update feedback
        existing_feedback = self.feedback_repo.get_by_session(session_id)
        if existing_feedback:
            feedback = existing_feedback
        else:
            feedback = Feedback(session_id=session_id)
        
        # Set aggregate scores
        feedback.empathy_score = empathy_score
        feedback.spikes_completion_score = spikes_score
        feedback.overall_score = overall_score
        
        # Set AFCE-structured metrics (only if data exists)
        feedback.eo_counts_by_dimension = json.dumps(eo_counts_by_dimension) if eo_counts_by_dimension is not None else None
        feedback.elicitation_counts_by_type = json.dumps(elicitation_counts_by_type) if elicitation_counts_by_type is not None else None
        feedback.response_counts_by_type = json.dumps(response_counts_by_type) if response_counts_by_type is not None else None
        
        # Placeholders for Part 2 (only set if data exists)
        feedback.linkage_stats = json.dumps(linkage_stats) if linkage_stats is not None else None
        feedback.missed_opportunities_by_dimension = json.dumps(missed_opportunities_by_dimension) if missed_opportunities_by_dimension is not None else None
        feedback.eo_to_elicitation_links = json.dumps(eo_to_elicitation_links) if eo_to_elicitation_links is not None else None
        feedback.eo_to_response_links = json.dumps(eo_to_response_links) if eo_to_response_links is not None else None
        feedback.missed_opportunities = json.dumps(missed_opportunities) if missed_opportunities is not None else None

        # Set SPIKES metrics (only if data exists)
        feedback.spikes_coverage = json.dumps(spikes_coverage) if spikes_coverage is not None else None
        feedback.spikes_timestamps = json.dumps(spikes_timestamps) if spikes_timestamps is not None else None
        feedback.spikes_strategies = json.dumps(spikes_strategies) if spikes_strategies is not None else None

        # Set questioning metrics (only if data exists)
        feedback.question_breakdown = json.dumps(question_breakdown) if question_breakdown is not None else None

        # Set metadata (only if data exists)
        feedback.bias_probe_info = json.dumps(bias_probe_info) if bias_probe_info is not None else None
        feedback.evaluator_meta = json.dumps(evaluator_meta) if evaluator_meta is not None else None
        feedback.latency_ms_avg = latency_ms_avg  # Always include (0.0 is valid)
        
        # Set textual feedback (only if data exists)
        feedback.strengths = strengths if strengths and strengths.strip() else None
        feedback.areas_for_improvement = improvements if improvements and improvements.strip() else None
        feedback.detailed_feedback = f"Overall Score: {overall_score:.1f}/10" if overall_score >= 0 else None
        
        if existing_feedback:
            saved_feedback = self.feedback_repo.update(feedback)
        else:
            saved_feedback = self.feedback_repo.create(feedback)
        
        # Deserialize JSON fields before creating response (only AFCE + SPIKES + approved metadata)
        saved_feedback.eo_counts_by_dimension = self._deserialize_json_field(saved_feedback.eo_counts_by_dimension)
        saved_feedback.elicitation_counts_by_type = self._deserialize_json_field(saved_feedback.elicitation_counts_by_type)
        saved_feedback.response_counts_by_type = self._deserialize_json_field(saved_feedback.response_counts_by_type)
        saved_feedback.linkage_stats = self._deserialize_json_field(saved_feedback.linkage_stats)
        saved_feedback.missed_opportunities_by_dimension = self._deserialize_json_field(saved_feedback.missed_opportunities_by_dimension)
        saved_feedback.eo_to_elicitation_links = self._deserialize_json_field(saved_feedback.eo_to_elicitation_links)
        saved_feedback.eo_to_response_links = self._deserialize_json_field(saved_feedback.eo_to_response_links)
        saved_feedback.missed_opportunities = self._deserialize_json_field(saved_feedback.missed_opportunities)
        saved_feedback.spikes_coverage = self._deserialize_json_field(saved_feedback.spikes_coverage)
        saved_feedback.spikes_timestamps = self._deserialize_json_field(saved_feedback.spikes_timestamps)
        saved_feedback.spikes_strategies = self._deserialize_json_field(saved_feedback.spikes_strategies)
        saved_feedback.question_breakdown = self._deserialize_json_field(saved_feedback.question_breakdown)
        saved_feedback.bias_probe_info = self._deserialize_json_field(saved_feedback.bias_probe_info)
        saved_feedback.evaluator_meta = self._deserialize_json_field(saved_feedback.evaluator_meta)
        
        # Add span-level data for turn-level analysis (already collected above)
        saved_feedback.eo_spans = eo_spans
        saved_feedback.elicitation_spans = elicitation_spans
        saved_feedback.response_spans = response_spans
        
        # Add relations placeholder (will be populated in Part 2)
        saved_feedback.relations = None  # Will be computed from relations_json in Part 2

        # Create response and let exclude_none=True and _remove_empty_values handle cleanup
        response = FeedbackResponse.model_validate(saved_feedback)
        return response
    
    # AFCE span-based metric calculation methods
    
    def _extract_spans_from_turns(self, turns: list) -> list[dict[str, Any]]:
        """Extract all spans from turns' spans_json."""
        all_spans = []
        for turn in turns:
            if turn.spans_json:
                spans = self._deserialize_json_field(turn.spans_json)
                if spans and isinstance(spans, list):
                    # Add turn_id and turn_number to each span for reference
                    for span in spans:
                        span["turn_id"] = turn.id
                        span["turn_number"] = turn.turn_number
                    all_spans.extend(spans)
        return all_spans
    
    def _calculate_eo_counts_by_dimension(self, all_spans: list) -> dict[str, Any]:
        """Calculate EO counts by AFCE dimension and explicit/implicit."""
        counts = {
            "Feeling": {"explicit": 0, "implicit": 0},
            "Judgment": {"explicit": 0, "implicit": 0},
            "Appreciation": {"explicit": 0, "implicit": 0},
        }
        
        for span in all_spans:
            if span.get("span_type") == "eo":
                dimension = span.get("dimension")
                explicit_implicit = span.get("explicit_or_implicit")
                if dimension in counts and explicit_implicit in ["explicit", "implicit"]:
                    counts[dimension][explicit_implicit] += 1
        
        return counts
    
    def _calculate_elicitation_counts_by_type(self, all_spans: list) -> dict[str, Any]:
        """Calculate elicitation counts by type (direct/indirect) and dimension."""
        counts = {
            "direct": {"Feeling": 0, "Judgment": 0, "Appreciation": 0},
            "indirect": {"Feeling": 0, "Judgment": 0, "Appreciation": 0},
        }
        
        for span in all_spans:
            if span.get("span_type") == "elicitation":
                elicitation_type = span.get("type")
                dimension = span.get("dimension")
                if elicitation_type in counts and dimension in counts[elicitation_type]:
                    counts[elicitation_type][dimension] += 1
        
        return counts
    
    def _calculate_response_counts_by_type(self, all_spans: list) -> dict[str, int]:
        """Calculate response counts by AFCE type (understanding/sharing/acceptance)."""
        counts = {
            "understanding": 0,
            "sharing": 0,
            "acceptance": 0,
        }
        
        for span in all_spans:
            if span.get("span_type") == "response":
                response_type = span.get("type")
                if response_type in counts:
                    counts[response_type] += 1
        
        return counts
    
    def _link_eos_to_responses(
        self,
        eo_spans: list[dict],
        response_spans: list[dict],
        turns: list,
    ) -> dict[int, list[dict]]:
        """Link EOs to responses within the next 2 clinician turns.
        
        Returns:
            dict mapping EO turn_number to list of linked response spans
        """
        # Create a map of turn_number -> turn for quick lookup
        turn_map = {turn.turn_number: turn for turn in turns}
        
        # Group response spans by turn_number
        responses_by_turn = {}
        for response_span in response_spans:
            turn_num = response_span.get("turn_number")
            if turn_num is not None:
                if turn_num not in responses_by_turn:
                    responses_by_turn[turn_num] = []
                responses_by_turn[turn_num].append(response_span)
        
        # For each EO, find responses in next 2 clinician turns
        eo_to_responses = {}
        
        for eo_span in eo_spans:
            eo_turn_num = eo_span.get("turn_number")
            if eo_turn_num is None:
                continue
            
            # Find the EO's turn
            eo_turn = turn_map.get(eo_turn_num)
            if not eo_turn:
                continue
            
            # Only link if EO is from a patient turn (assistant role)
            if eo_turn.role != "assistant":
                continue
            
            linked_responses = []
            
            # Look ahead at next 2 clinician turns (user role)
            clinician_turns_checked = 0
            current_turn_num = eo_turn_num + 1
            
            while clinician_turns_checked < 2 and current_turn_num in turn_map:
                candidate_turn = turn_map[current_turn_num]
                
                # Only check clinician turns (user role)
                if candidate_turn.role == "user":
                    clinician_turns_checked += 1
                    # Add any response spans from this turn
                    if current_turn_num in responses_by_turn:
                        linked_responses.extend(responses_by_turn[current_turn_num])
                
                current_turn_num += 1
            
            # Store linked responses (can be empty list)
            eo_to_responses[eo_turn_num] = linked_responses
        
        return eo_to_responses
    
    def _calculate_empathy_score_from_afce(
        self,
        eo_counts_by_dimension: dict,
        response_counts_by_type: dict,
        all_spans: list,
        turns: list,
    ) -> float:
        """Calculate composite empathy score from AFCE-style EO→response performance.
        
        Components:
        - EO Coverage Score (0-10): 50% weight
        - Dimension Matching Score (0-10): 30% weight  
        - Timing/Sequencing Score (0-10): 20% weight
        """
        # Extract EO and response spans
        eo_spans = [s for s in all_spans if s.get("span_type") == "eo"]
        response_spans = [s for s in all_spans if s.get("span_type") == "response"]
        
        # If no EOs detected, return 0.0
        if not eo_spans:
            return 0.0
        
        # Link EOs to responses
        eo_to_responses = self._link_eos_to_responses(eo_spans, response_spans, turns)
        
        # 2.1 EO Coverage Score
        addressed_explicit = 0
        addressed_implicit = 0
        missed_explicit = 0
        missed_implicit = 0
        
        for eo_span in eo_spans:
            eo_turn_num = eo_span.get("turn_number")
            dimension = eo_span.get("dimension")
            explicit_implicit = eo_span.get("explicit_or_implicit")
            
            if eo_turn_num is None or explicit_implicit not in ["explicit", "implicit"]:
                continue
            
            # Check if this EO has at least one linked response
            has_response = eo_turn_num in eo_to_responses and len(eo_to_responses[eo_turn_num]) > 0
            
            if has_response:
                if explicit_implicit == "explicit":
                    addressed_explicit += 1
                else:
                    addressed_implicit += 1
            else:
                if explicit_implicit == "explicit":
                    missed_explicit += 1
                else:
                    missed_implicit += 1
        
        total_eos = len(eo_spans)
        total_explicit = addressed_explicit + missed_explicit
        total_implicit = addressed_implicit + missed_implicit
        
        if total_eos == 0:
            eo_coverage_score = 0.0
        else:
            # Calculate raw coverage
            coverage_raw = (
                1.0 * addressed_explicit +
                1.2 * addressed_implicit -
                1.5 * missed_explicit -
                1.0 * missed_implicit
            )
            
            # Normalize to 0-10
            max_possible = max(1, 1.2 * total_eos)  # best case: all implicit and addressed
            min_possible = -(1.5 * total_explicit + 1.0 * total_implicit)  # worst case: all missed
            
            if max_possible - min_possible == 0:
                coverage_norm_clamped = 0.0
            else:
                coverage_norm = (coverage_raw - min_possible) / (max_possible - min_possible)
                coverage_norm_clamped = min(1.0, max(0.0, coverage_norm))
            
            eo_coverage_score = coverage_norm_clamped * 10.0
        
        # 2.2 Dimension Matching Score
        num_addressed_eos = addressed_explicit + addressed_implicit
        total_match_points = 0.0
        
        if num_addressed_eos > 0:
            for eo_span in eo_spans:
                eo_turn_num = eo_span.get("turn_number")
                dimension = eo_span.get("dimension")
                
                if eo_turn_num is None or eo_turn_num not in eo_to_responses:
                    continue
                
                linked_responses = eo_to_responses[eo_turn_num]
                if not linked_responses:
                    continue
                
                # Check if at least one response is dimension-appropriate
                matched = False
                partially_matched = False
                
                for response_span in linked_responses:
                    response_type = response_span.get("type")
                    
                    if dimension == "Feeling":
                        # Any response type counts as matched for Feeling
                        matched = True
                        break
                    elif dimension == "Judgment":
                        # sharing or understanding count as matched
                        if response_type in ["sharing", "understanding"]:
                            matched = True
                            break
                        elif response_type == "acceptance":
                            partially_matched = True
                    elif dimension == "Appreciation":
                        # sharing or acceptance count as matched
                        if response_type in ["sharing", "acceptance"]:
                            matched = True
                            break
                        elif response_type == "understanding":
                            partially_matched = True
                
                if matched:
                    total_match_points += 1.0
                elif partially_matched:
                    total_match_points += 0.5
                # If no response matched, already penalized in coverage, so add 0
            
            dimension_matching_score = (total_match_points / num_addressed_eos) * 10.0
        else:
            dimension_matching_score = 0.0
        
        # 2.3 Timing/Sequencing Score
        total_timing_points = 0.0
        
        if num_addressed_eos > 0:
            # Create a map of turn_number -> turn for quick lookup
            turn_map = {turn.turn_number: turn for turn in turns}
            
            for eo_span in eo_spans:
                eo_turn_num = eo_span.get("turn_number")
                
                if eo_turn_num is None or eo_turn_num not in eo_to_responses:
                    continue
                
                linked_responses = eo_to_responses[eo_turn_num]
                if not linked_responses:
                    continue
                
                # Find the earliest clinician turn with a response
                earliest_response_turn = None
                for response_span in linked_responses:
                    resp_turn_num = response_span.get("turn_number")
                    if resp_turn_num and resp_turn_num in turn_map:
                        resp_turn = turn_map[resp_turn_num]
                        if resp_turn.role == "user":  # clinician turn
                            if earliest_response_turn is None or resp_turn_num < earliest_response_turn:
                                earliest_response_turn = resp_turn_num
                
                if earliest_response_turn is None:
                    continue
                
                # Count clinician turns between EO and response (excluding response turn itself)
                clinician_turn_count = 0
                current_turn_num = eo_turn_num + 1
                
                while current_turn_num < earliest_response_turn:
                    if current_turn_num in turn_map:
                        turn = turn_map[current_turn_num]
                        if turn.role == "user":  # clinician turn
                            clinician_turn_count += 1
                    current_turn_num += 1
                
                # Assign timing score
                # If response is in first clinician turn after EO (clinician_turn_count == 0), score = 1.0
                # If response is in second clinician turn after EO (clinician_turn_count == 1), score = 0.5
                if clinician_turn_count == 0:
                    total_timing_points += 1.0  # response in next clinician turn
                elif clinician_turn_count == 1:
                    total_timing_points += 0.5  # response in second clinician turn
                # else: 0 (later or same turn)
            
            timing_sequencing_score = (total_timing_points / num_addressed_eos) * 10.0
        else:
            timing_sequencing_score = 0.0
        
        # 2.4 Final Empathy Score
        empathy_score = (
            0.5 * eo_coverage_score +
            0.3 * dimension_matching_score +
            0.2 * timing_sequencing_score
        )
        
        # Clamp to [0, 10] and round
        empathy_score = min(10.0, max(0.0, empathy_score))
        return round(empathy_score, 2)
    
    def _compute_eo_linking(
        self,
        eo_spans: list,
        response_spans: list,
        elicitation_spans: list,
        turns: list,
    ) -> tuple[list, list, dict]:
        """Compute EO→response links, missed opportunities, and linkage stats.
        
        Returns:
            Tuple of (eo_to_response_links, missed_opportunities, linkage_stats)
        """
        # Link EOs to responses
        eo_to_responses_map = self._link_eos_to_responses(eo_spans, response_spans, turns)
        
        # Build eo_to_response_links list
        eo_to_response_links = []
        missed_opportunities = []
        addressed_count = 0
        missed_count = 0
        
        # Create span ID mapping (use turn_number + index as ID)
        span_id_map = {}
        next_id = 1
        
        # Assign IDs to EOs
        eo_id_map = {}
        for eo in eo_spans:
            eo_id = f"eo_{next_id}"
            eo_id_map[id(eo)] = eo_id
            span_id_map[eo_id] = eo
            next_id += 1
        
        # Assign IDs to responses (use index-based matching since objects may differ)
        response_id_map = {}
        response_match_key_map = {}  # Map from (turn_number, start_char, end_char, text) to ID
        for i, resp in enumerate(response_spans):
            resp_id = f"resp_{next_id}"
            response_id_map[i] = resp_id
            span_id_map[resp_id] = resp
            # Create a match key for linking
            match_key = (
                resp.get("turn_number"),
                resp.get("start_char"),
                resp.get("end_char"),
                resp.get("text", "")[:50],  # First 50 chars for matching
            )
            response_match_key_map[match_key] = resp_id
            next_id += 1
        
        # Create links
        for eo in eo_spans:
            eo_turn_num = eo.get("turn_number")
            eo_id = eo_id_map.get(id(eo))
            
            if eo_turn_num is None or eo_id is None:
                continue
            
            linked_responses = eo_to_responses_map.get(eo_turn_num, [])
            
            if linked_responses:
                addressed_count += 1
                # Create links for each linked response
                for resp in linked_responses:
                    # Match response by turn_number, start_char, end_char, and text
                    match_key = (
                        resp.get("turn_number"),
                        resp.get("start_char"),
                        resp.get("end_char"),
                        resp.get("text", "")[:50],
                    )
                    resp_id = response_match_key_map.get(match_key)
                    if resp_id:
                        eo_to_response_links.append({
                            "source_span_id": eo_id,
                            "target_span_id": resp_id,
                            "relation_type": "responds_to",
                            "confidence": 0.9,
                        })
            else:
                missed_count += 1
                missed_opportunities.append({
                    "span_id": eo_id,
                    "turn_number": eo_turn_num,
                    "dimension": eo.get("dimension"),
                    "explicit_or_implicit": eo.get("explicit_or_implicit"),
                    "text": eo.get("text", "")[:100],  # Truncate
                })
        
        total_eos = len(eo_spans)
        linkage_stats = {
            "total_eos": total_eos,
            "addressed_count": addressed_count,
            "missed_count": missed_count,
            "addressed_rate": addressed_count / total_eos if total_eos > 0 else 0.0,
            "missed_rate": missed_count / total_eos if total_eos > 0 else 0.0,
        }
        
        # Convert list to dict keyed by EO ID for easier lookup
        eo_to_response_links_dict = {}
        for link in eo_to_response_links:
            source_id = link["source_span_id"]
            if source_id not in eo_to_response_links_dict:
                eo_to_response_links_dict[source_id] = []
            eo_to_response_links_dict[source_id].append(link)
        
        return eo_to_response_links_dict, missed_opportunities, linkage_stats
    
    def _compute_eo_to_elicitation_links(
        self,
        eo_spans: list,
        elicitation_spans: list,
        turns: list,
    ) -> list:
        """Compute EO→elicitation links.
        
        Returns:
            List of links with source_span_id, target_span_id, relation_type
        """
        links = []
        
        # Create span ID mapping
        eo_id_map = {}
        next_id = 1
        
        for eo in eo_spans:
            eo_id = f"eo_{next_id}"
            eo_id_map[id(eo)] = eo_id
            next_id += 1
        
        elicitation_id_map = {}
        for el in elicitation_spans:
            el_id = f"elic_{next_id}"
            elicitation_id_map[id(el)] = el_id
            next_id += 1
        
        # Create a map of turn_number -> elicitation spans
        elicitations_by_turn = {}
        for el in elicitation_spans:
            turn_num = el.get("turn_number")
            if turn_num is not None:
                if turn_num not in elicitations_by_turn:
                    elicitations_by_turn[turn_num] = []
                elicitations_by_turn[turn_num].append(el)
        
        # For each EO, find elicitations in the same or previous clinician turns
        turn_map = {turn.turn_number: turn for turn in turns}
        
        for eo in eo_spans:
            eo_turn_num = eo.get("turn_number")
            eo_id = eo_id_map.get(id(eo))
            eo_dimension = eo.get("dimension")
            
            if eo_turn_num is None or eo_id is None:
                continue
            
            # Find the EO's turn
            eo_turn = turn_map.get(eo_turn_num)
            if not eo_turn or eo_turn.role != "assistant":  # Patient turn
                continue
            
            # Look back at previous clinician turns (up to 2 turns back)
            # to find elicitations that may have prompted this EO
            turns_checked = 0
            current_turn_num = eo_turn_num - 1
            
            while turns_checked < 2 and current_turn_num > 0:
                if current_turn_num in turn_map:
                    candidate_turn = turn_map[current_turn_num]
                    if candidate_turn.role == "user":  # Clinician turn
                        turns_checked += 1
                        # Check if there are elicitations in this turn matching the EO dimension
                        if current_turn_num in elicitations_by_turn:
                            for el in elicitations_by_turn[current_turn_num]:
                                el_dimension = el.get("dimension")
                                el_id = elicitation_id_map.get(id(el))
                                # Match if dimensions match or if elicitation is general
                                if el_id and (el_dimension == eo_dimension or el_dimension == "Feeling"):
                                    links.append({
                                        "source_span_id": eo_id,
                                        "target_span_id": el_id,
                                        "relation_type": "elicits",
                                        "confidence": 0.85,
                                    })
                
                current_turn_num -= 1
        
        # Convert list to dict keyed by EO ID for easier lookup
        eo_to_elicitation_links_dict = {}
        for link in links:
            source_id = link["source_span_id"]
            if source_id not in eo_to_elicitation_links_dict:
                eo_to_elicitation_links_dict[source_id] = []
            eo_to_elicitation_links_dict[source_id].append(link)
        
        return eo_to_elicitation_links_dict
    
    def _compute_missed_opportunities_by_dimension(
        self,
        missed_opportunities: list,
        eo_spans: list,
    ) -> dict:
        """Compute missed opportunities counts by dimension.
        
        Returns:
            Dict with counts per dimension
        """
        counts = {
            "Feeling": 0,
            "Judgment": 0,
            "Appreciation": 0,
        }
        
        for missed in missed_opportunities:
            dimension = missed.get("dimension")
            if dimension in counts:
                counts[dimension] += 1
        
        return counts
    
    def _collect_span_lists(
        self,
        all_spans: list,
    ) -> tuple[list, list, list]:
        """Collect spans into separate lists by type for turn-level analysis."""
        eo_spans = []
        elicitation_spans = []
        response_spans = []
        
        for span in all_spans:
            span_type = span.get("span_type")
            if span_type == "eo":
                eo_spans.append(span)
            elif span_type == "elicitation":
                elicitation_spans.append(span)
            elif span_type == "response":
                response_spans.append(span)
        
        return eo_spans, elicitation_spans, response_spans
    
    def _calculate_spikes_completion(
        self, 
        session, 
        turns: list,
        all_spans: list,
    ) -> float:
        """Calculate SPIKES protocol completion score.
        
        Components:
        - Coverage (0-1): 40% weight
        - Sequence Correctness (0-1): 40% weight
        - Empathy During E Stage (0-1): 20% weight
        """
        # Extract response spans for empathy detection
        response_spans = [s for s in all_spans if s.get("span_type") == "response"]
        
        # 3.1 Coverage Component
        stages_reached = set()
        for turn in turns:
            if turn.spikes_stage:
                # Normalize stage names (handle both "summary" and "S2", etc.)
                stage = turn.spikes_stage.lower()
                # Map common variations
                if stage in ["s2", "strategy", "summary"]:
                    stage = "strategy"
                elif stage == "s" or stage == "setting":
                    # Skip Setting from denominator
                    continue
                stages_reached.add(stage)
        
        # Consider only P, I, K, E, Strategy (exclude Setting)
        target_stages = {"perception", "invitation", "knowledge", "empathy", "strategy"}
        covered_stages = stages_reached & target_stages
        
        coverage_fraction = len(covered_stages) / len(target_stages) if target_stages else 0.0
        coverage_score = coverage_fraction  # in [0, 1]
        
        # 3.2 Sequence Correctness Component
        # Expected order: P → I → K → E → Strategy
        expected_order = ["perception", "invitation", "knowledge", "empathy", "strategy"]
        
        # Get timestamps/turn_numbers for each stage
        stage_timestamps = {}
        for turn in turns:
            if turn.spikes_stage:
                stage = turn.spikes_stage.lower()
                # Map variations
                if stage in ["s2", "strategy", "summary"]:
                    stage = "strategy"
                elif stage in ["s", "setting"]:
                    continue
                
                if stage in expected_order:
                    # Use turn_number as proxy for sequence (lower = earlier)
                    if stage not in stage_timestamps:
                        stage_timestamps[stage] = turn.turn_number
        
        # Check consecutive pairs
        correct_pairs = 0
        num_pairs_present = 0
        
        for i in range(len(expected_order) - 1):
            earlier_stage = expected_order[i]
            later_stage = expected_order[i + 1]
            
            # Both stages must be present to form a pair
            if earlier_stage in stage_timestamps and later_stage in stage_timestamps:
                num_pairs_present += 1
                # Check if earlier stage occurs before later stage
                if stage_timestamps[earlier_stage] < stage_timestamps[later_stage]:
                    correct_pairs += 1
        
        if num_pairs_present == 0:
            sequence_fraction = 0.0
        else:
            sequence_fraction = correct_pairs / num_pairs_present
        
        sequence_score = sequence_fraction  # in [0, 1]
        
        # 3.3 Empathy During E Stage Component
        # Find turns tagged as empathy stage
        empathy_turns = [turn for turn in turns if turn.spikes_stage and turn.spikes_stage.lower() == "empathy"]
        
        if not empathy_turns:
            empathy_during_e = 0.0
        else:
            # For each empathy turn, check if it has response spans
            empathy_turns_with_response = 0
            for empathy_turn in empathy_turns:
                turn_num = empathy_turn.turn_number
                # Check if there are any response spans in this turn
                has_response = any(
                    resp_span.get("turn_number") == turn_num 
                    for resp_span in response_spans
                )
                if has_response:
                    empathy_turns_with_response += 1
            
            total_empathy_turns = len(empathy_turns)
            empathy_during_e = empathy_turns_with_response / total_empathy_turns if total_empathy_turns > 0 else 0.0
        
        # 3.4 Final SPIKES Score
        spikes_score_0_1 = (
            0.4 * coverage_score +
            0.4 * sequence_score +
            0.2 * empathy_during_e
        )
        
        spikes_completion_score = spikes_score_0_1 * 10.0
        
        # Clamp to [0, 10] and round
        spikes_completion_score = min(10.0, max(0.0, spikes_completion_score))
        return round(spikes_completion_score, 2)
    
    def _calculate_question_breakdown(self, turns: list) -> dict[str, Any]:
        """Calculate question breakdown: open, closed, and eliciting questions."""
        open_count = 0
        closed_count = 0
        eliciting_count = 0
        
        for turn in turns:
            if turn.role == "user" and turn.metrics_json:
                metrics = self._parse_metrics_json(turn.metrics_json)
                if metrics:
                    q_type = metrics.get("question_type")
                    if q_type == "open":
                        open_count += 1
                    elif q_type == "closed":
                        closed_count += 1
                    
                    # Check if question is eliciting (asks for emotion/feeling)
                    text_lower = turn.text.lower()
                    eliciting_keywords = ["feel", "feeling", "emotion", "emotions", "how do you", "what do you feel"]
                    if any(keyword in text_lower for keyword in eliciting_keywords):
                        eliciting_count += 1
        
        total = open_count + closed_count
        return {
            "open": open_count,
            "closed": closed_count,
            "eliciting": eliciting_count,
            "ratio_open": open_count / total if total > 0 else 0,
        }
    
    def _analyze_spikes_coverage(self, turns: list) -> dict[str, Any]:
        """Analyze coverage of SPIKES stages."""
        covered_stages = set()
        for turn in turns:
            if turn.spikes_stage:
                covered_stages.add(turn.spikes_stage)
        
        all_stages = ["S", "P", "I", "K", "E", "S2"]
        covered_list = sorted(list(covered_stages))
        percent = len(covered_stages) / len(all_stages) if all_stages else 0.0
        
        return {
            "covered": covered_list,
            "percent": percent,
        }
    
    def _generate_textual_feedback(
        self,
        empathy_score: float,
        communication_score: float | None,
        spikes_score: float,
        question_breakdown: dict,
        eo_spans: list = None,
    ) -> tuple[str, str]:
        """Generate strengths and improvement areas."""
        strengths = []
        improvements = []
        
        # Check if no EOs were detected
        if eo_spans is None:
            eo_spans = []
        
        if not eo_spans:
            improvements.append("No AFCE empathy opportunities were detected in this session")
        elif empathy_score >= 7:
            strengths.append("Excellent use of empathetic language")
        elif empathy_score > 0:
            improvements.append("Consider using more empathetic phrases")
        else:
            improvements.append("Work on responding to empathy opportunities")
        
        if question_breakdown.get("ratio_open", 0) > 0.6:
            strengths.append("Good use of open-ended questions")
        else:
            improvements.append("Try asking more open-ended questions")
        
        if spikes_score >= 8:
            strengths.append("Comprehensive coverage of SPIKES protocol")
        else:
            improvements.append("Work on covering all SPIKES protocol stages")
        
        return "\n".join(strengths), "\n".join(improvements)
    
    # SPIKES metrics
    def _calculate_spikes_timestamps(self, turns: list) -> dict[str, Any]:
        """Track when each SPIKES stage started and ended."""
        timestamps = {}
        stage_starts = {}
        
        for turn in turns:
            if turn.spikes_stage:
                stage = turn.spikes_stage
                if stage not in stage_starts:
                    stage_starts[stage] = turn.timestamp
                    timestamps[stage] = {
                        "start_ts": str(turn.timestamp),
                        "end_ts": str(turn.timestamp),
                    }
                else:
                    timestamps[stage]["end_ts"] = str(turn.timestamp)
        
        return timestamps
    
    def _identify_spikes_strategies(self, turns: list) -> dict[str, list[dict[str, Any]]]:
        """Map strategies used per SPIKES stage."""
        strategies = {}
        
        strategy_keywords = {
            "summarize": [
                "summary", "summarize", "recap", "to summarize",
                "let me summarize", "in summary", "to recap"
            ],
            "acknowledge": [
                "understand", "acknowledge", "recognize", "i see",
                "i hear you", "i get it", "i understand"
            ],
            "explore": [
                "explore", "tell me more", "can you", "would you like to",
                "how do you feel", "what are your thoughts", "help me understand"
            ],
            "validate": [
                "valid", "makes sense", "understandable", "that's normal",
                "that's understandable", "i can see why"
            ],
            "empathize": [
                "i'm sorry", "that must be", "i can imagine", "that sounds",
                "i understand how", "that must feel"
            ],
            "clarify": [
                "clarify", "let me clarify", "to be clear", "just to make sure",
                "can you clarify", "help me understand"
            ],
        }
        
        for turn in turns:
            if turn.spikes_stage and turn.role == "user":  # User (doctor) uses strategies
                stage = turn.spikes_stage
                if stage not in strategies:
                    strategies[stage] = []
                
                text_lower = turn.text.lower()
                # Check for multiple strategies (don't break after first match)
                matched_strategies = []
                for strategy, keywords in strategy_keywords.items():
                    if any(keyword in text_lower for keyword in keywords):
                        matched_strategies.append(strategy)
                
                # Add all matched strategies
                for strategy in matched_strategies:
                    strategies[stage].append({
                        "strategy": strategy,
                        "turn": turn.turn_number,
                    })
        
        return strategies
    
    # Questioning & style metrics
    def _calculate_interruptions(self, turns: list) -> int:
        """Count interruptions (assistant speaking when user was speaking)."""
        if not turns:
            return 0
        
        count = 0
        INTERRUPTION_THRESHOLD_SECONDS = 2.0  # Less than 2 seconds between turns
        
        # Sort turns by timestamp to ensure correct order
        sorted_turns = sorted(turns, key=lambda t: t.timestamp)
        
        for i in range(1, len(sorted_turns)):
            prev_turn = sorted_turns[i - 1]
            curr_turn = sorted_turns[i]
            
            # Check if previous turn was user and current is assistant
            if prev_turn.role == "user" and curr_turn.role == "assistant":
                # Calculate time difference
                time_diff = (curr_turn.timestamp - prev_turn.timestamp).total_seconds()
                
                # If time difference is very short, consider it an interruption
                if time_diff < INTERRUPTION_THRESHOLD_SECONDS:
                    count += 1
        
        return count
    
    def _calculate_reflections_interpretations(self, turns: list) -> dict[str, int]:
        """Count reflections vs interpretations."""
        reflections = 0
        interpretations = 0
        
        reflection_keywords = [
            "it sounds like", "you're saying", "so you", "i hear you",
            "i understand", "i see", "let me make sure i understand"
        ]
        interpretation_keywords = [
            "i think", "perhaps", "maybe", "it seems", "you might",
            "it appears", "i suspect", "my interpretation"
        ]
        
        for turn in turns:
            if turn.role == "user":  # Fixed: should analyze user (doctor) turns
                text_lower = turn.text.lower()
                if any(keyword in text_lower for keyword in reflection_keywords):
                    reflections += 1
                elif any(keyword in text_lower for keyword in interpretation_keywords):
                    interpretations += 1
        
        return {
            "reflections": reflections,
            "interpretations": interpretations,
        }
    
    # Tone & safety metrics
    def _calculate_tone_summary(self, turns: list) -> dict[str, Any]:
        """Analyze tone (calm and clear rate)."""
        calm_clear_count = 0
        total_turns = 0
        
        for turn in turns:
            if turn.role == "user" and turn.metrics_json:
                metrics = self._parse_metrics_json(turn.metrics_json)
                if metrics:
                    tone = metrics.get("tone", {})
                    if tone.get("calm", False) and tone.get("clear", False):
                        calm_clear_count += 1
                    total_turns += 1
        
        calm_clear_rate = calm_clear_count / total_turns if total_turns > 0 else 0.0
        
        return {
            "calm_clear_rate": calm_clear_rate,
            "sample_n": total_turns,
        }
    
    def _identify_prohibited_behaviors(self, turns: list) -> list[dict[str, Any]]:
        """Detect prohibited behaviors like invalidations, dismissals."""
        prohibited = []
        
        invalidation_keywords = [
            "that's not true", "you're wrong", "that doesn't make sense",
            "that's incorrect", "you're mistaken", "no, that's not right"
        ]
        dismissal_keywords = [
            "don't worry", "it's fine", "just", "only", "it's okay",
            "no big deal", "don't stress", "calm down", "relax"
        ]
        
        for turn in turns:
            if turn.role == "user":  # Fixed: should analyze user (doctor) turns, not assistant
                text_lower = turn.text.lower()
                behavior_type = None
                
                if any(keyword in text_lower for keyword in invalidation_keywords):
                    behavior_type = "invalidation"
                elif any(keyword in text_lower for keyword in dismissal_keywords):
                    behavior_type = "dismissal"
                
                if behavior_type:
                    prohibited.append({
                        "turn": turn.turn_number,
                        "type": behavior_type,
                    })
        
        return prohibited
    
    def _identify_deescalation_strategies(self, turns: list) -> dict[str, Any]:
        """Track deescalation techniques used."""
        strategies = {
            "autonomy": 0,
            "limit_setting": 0,
            "problem_solving": 0,
        }
        
        autonomy_keywords = [
            "your choice", "you decide", "up to you", "your decision",
            "it's your call", "you have the option", "you can choose"
        ]
        limit_keywords = [
            "boundary", "limit", "cannot", "not allowed", "we need to",
            "let's establish", "set boundaries"
        ]
        problem_solving_keywords = [
            "solution", "solve", "address", "fix", "resolve",
            "let's work together", "how can we", "what can we do"
        ]
        
        for turn in turns:
            if turn.role == "user":  # Fixed: should analyze user (doctor) turns
                text_lower = turn.text.lower()
                if any(keyword in text_lower for keyword in autonomy_keywords):
                    strategies["autonomy"] += 1
                if any(keyword in text_lower for keyword in limit_keywords):
                    strategies["limit_setting"] += 1
                if any(keyword in text_lower for keyword in problem_solving_keywords):
                    strategies["problem_solving"] += 1
        
        strategies["observed_any"] = any(count > 0 for count in strategies.values())
        
        return strategies
    
    # Performance metrics
    def _calculate_latency_ms_avg(self, turns: list) -> float:
        """Calculate average response latency in milliseconds."""
        latencies = []
        
        for turn in turns:
            if turn.role == "assistant" and turn.metrics_json:
                metrics = self._parse_metrics_json(turn.metrics_json)
                if metrics:
                    latency = metrics.get("latency_ms")
                    if latency:
                        latencies.append(float(latency))
        
        return sum(latencies) / len(latencies) if latencies else 0.0

