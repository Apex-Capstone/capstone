import { useState, useMemo } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { supabase } from '@/lib/supabase'
import api from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Check, Eye, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import apexLogo from '@/assets/apex-capstone-logo.png'

const GENDER_OPTIONS = [
  { value: '', label: 'Select gender (optional)' },
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
]

const RACE_OPTIONS = [
  { value: '', label: 'Select race / ethnicity (optional)' },
  { value: 'american_indian', label: 'American Indian or Alaska Native' },
  { value: 'asian', label: 'Asian' },
  { value: 'black', label: 'Black or African American' },
  { value: 'hispanic', label: 'Hispanic or Latino' },
  { value: 'pacific_islander', label: 'Native Hawaiian or Pacific Islander' },
  { value: 'white', label: 'White' },
  { value: 'multiracial', label: 'Two or More Races' },
  { value: 'other', label: 'Other' },
  { value: 'prefer_not_to_say', label: 'Prefer not to say' },
]

const YEAR_OF_STUDY_OPTIONS = [
  { value: '', label: 'Select year of study (optional)' },
  { value: 'undergrad', label: 'Undergraduate (Pre-med)' },
  { value: 'ms1', label: 'Medical School — Year 1' },
  { value: 'ms2', label: 'Medical School — Year 2' },
  { value: 'ms3', label: 'Medical School — Year 3' },
  { value: 'ms4', label: 'Medical School — Year 4' },
  { value: 'resident', label: 'Residency' },
  { value: 'fellow', label: 'Fellowship' },
  { value: 'attending', label: 'Attending / Practicing Physician' },
  { value: 'other', label: 'Other' },
]

const PASSWORD_RULES = [
  { key: 'length', label: 'At least 8 characters', test: (p: string) => p.length >= 8 },
  { key: 'upper', label: 'One uppercase letter', test: (p: string) => /[A-Z]/.test(p) },
  { key: 'lower', label: 'One lowercase letter', test: (p: string) => /[a-z]/.test(p) },
  { key: 'number', label: 'One number', test: (p: string) => /\d/.test(p) },
  { key: 'special', label: 'One special character', test: (p: string) => /[^A-Za-z0-9]/.test(p) },
]

const SELECT_CLASS =
  'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50'

export const Signup = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [gender, setGender] = useState('')
  const [race, setRace] = useState('')
  const [yearOfStudy, setYearOfStudy] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  const passwordChecks = useMemo(
    () => PASSWORD_RULES.map((rule) => ({ ...rule, passed: rule.test(password) })),
    [password]
  )
  const passedCount = passwordChecks.filter((c) => c.passed).length
  const allPassed = passedCount === PASSWORD_RULES.length
  const strengthPct = (passedCount / PASSWORD_RULES.length) * 100
  const strengthColor =
    strengthPct <= 20
      ? 'bg-red-500'
      : strengthPct <= 40
        ? 'bg-orange-500'
        : strengthPct <= 60
          ? 'bg-yellow-500'
          : strengthPct <= 80
            ? 'bg-apex-500'
            : 'bg-apex-500'

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (!allPassed) {
      setError('Please meet all password requirements.')
      return
    }

    setLoading(true)

    try {
      const { data: existsResult } = await api.get<{ exists: boolean }>('/v1/auth/email-exists', {
        params: { email },
      })
      if (existsResult.exists) {
        setError('An account with this email already exists. Please sign in instead.')
        return
      }

      const metadata: Record<string, string> = {
        full_name: fullName,
        role: 'trainee',
      }
      if (gender) metadata.gender = gender
      if (race) metadata.race = race
      if (yearOfStudy) metadata.year_of_study = yearOfStudy

      const { error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: { data: metadata },
      })

      if (signUpError) {
        setError(signUpError.message)
        return
      }

      setSuccess(true)
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-md space-y-6">
          <div className="flex items-center justify-center gap-3">
            <img src={apexLogo} alt="APEX logo" className="h-14 w-14 rounded-2xl object-cover shadow-sm" />
            <div className="flex flex-col items-start leading-none">
                <span className="brand-font text-2xl font-bold tracking-[0.24em] text-apex-700">
                APEX
              </span>
              <span className="text-[10px] font-medium uppercase tracking-[0.2em] text-gray-500">
                AI Patient Experience Simulator
              </span>
            </div>
          </div>
          <Card>
            <CardHeader className="space-y-1">
              <CardTitle className="text-2xl font-bold">Check your email</CardTitle>
              <CardDescription>
                We've sent a verification link to <strong>{email}</strong>. Please check your inbox and click the link to verify your account.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link to="/login">
                <Button variant="outline" className="w-full">
                  Back to Sign in
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-8">
      <div className="w-full max-w-md space-y-6">
        <div className="flex items-center justify-center gap-3">
          <img src={apexLogo} alt="APEX logo" className="h-14 w-14 rounded-2xl object-cover shadow-sm" />
          <div className="flex flex-col items-start leading-none">
              <span className="brand-font text-2xl font-bold tracking-[0.24em] text-apex-700">
              APEX
            </span>
            <span className="text-[10px] font-medium uppercase tracking-[0.2em] text-gray-500">
              AI Patient Experience Simulator
            </span>
          </div>
        </div>
        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-bold">Create an account</CardTitle>
            <CardDescription>Start practicing with APEX</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name */}
            <div className="space-y-2">
              <label htmlFor="fullName" className="text-sm font-medium">
                Full Name <span className="text-red-500">*</span>
              </label>
              <Input
                id="fullName"
                type="text"
                placeholder="Your full name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                disabled={loading}
              />
            </div>

            {/* Email */}
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">
                Email <span className="text-red-500">*</span>
              </label>
              <Input
                id="email"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
              />
            </div>

            {/* Password */}
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium">
                Password <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Create a password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                  className="pr-10"
                />
                <button
                  type="button"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  className="absolute inset-y-0 right-0 flex items-center px-3 text-gray-500 bg-transparent border-0 shadow-none hover:bg-transparent active:bg-transparent focus:outline-none focus-visible:ring-0 hover:text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
                  onMouseDown={() => setShowPassword(true)}
                  onMouseUp={() => setShowPassword(false)}
                  onMouseLeave={() => setShowPassword(false)}
                  onTouchStart={() => setShowPassword(true)}
                  onTouchEnd={() => setShowPassword(false)}
                  onTouchCancel={() => setShowPassword(false)}
                  disabled={loading}
                >
                  <Eye className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-2 pt-1">
                {/* Strength bar */}
                <div className="h-1.5 w-full rounded-full bg-gray-200">
                  <div
                    className={cn('h-full rounded-full transition-all duration-300', password.length > 0 ? strengthColor : 'bg-gray-200')}
                    style={{ width: password.length > 0 ? `${strengthPct}%` : '0%' }}
                  />
                </div>

                {/* Requirement checklist — always visible */}
                <ul className="grid grid-cols-2 gap-x-4 gap-y-1">
                  {passwordChecks.map((check) => (
                    <li key={check.key} className="flex items-center gap-1.5 text-xs">
                      {check.passed ? (
                        <Check className="h-3 w-3 text-apex-500" />
                      ) : (
                        <X className="h-3 w-3 text-gray-300" />
                      )}
                      <span className={check.passed ? 'text-apex-600' : 'text-gray-400'}>
                        {check.label}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Optional fields */}
            <div className="border-t pt-4 mt-4">
              <p className="text-xs text-gray-500 mb-3">Optional information</p>

              <div className="space-y-4">
                {/* Gender */}
                <div className="space-y-2">
                  <label htmlFor="gender" className="text-sm font-medium">Gender</label>
                  <select
                    id="gender"
                    value={gender}
                    onChange={(e) => setGender(e.target.value)}
                    disabled={loading}
                    className={SELECT_CLASS}
                  >
                    {GENDER_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>

                {/* Race / Ethnicity */}
                <div className="space-y-2">
                  <label htmlFor="race" className="text-sm font-medium">Race / Ethnicity</label>
                  <select
                    id="race"
                    value={race}
                    onChange={(e) => setRace(e.target.value)}
                    disabled={loading}
                    className={SELECT_CLASS}
                  >
                    {RACE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>

                {/* Year of Study */}
                <div className="space-y-2">
                  <label htmlFor="yearOfStudy" className="text-sm font-medium">Year of Study</label>
                  <select
                    id="yearOfStudy"
                    value={yearOfStudy}
                    onChange={(e) => setYearOfStudy(e.target.value)}
                    disabled={loading}
                    className={SELECT_CLASS}
                  >
                    {YEAR_OF_STUDY_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {error && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">
                {error}
              </div>
            )}
              <Button type="submit" className="w-full" disabled={loading || !allPassed}>
                {loading ? 'Creating account...' : 'Create account'}
              </Button>
            </form>
            <p className="mt-4 text-center text-sm text-gray-600">
              Already have an account?{' '}
            <Link to="/login" className="font-medium text-apex-600 hover:text-apex-700">
                Sign in
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
