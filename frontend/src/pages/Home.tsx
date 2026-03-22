/**
 * Marketing landing for logged-out users; quick dashboard link when authenticated.
 */
import { Link } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Stethoscope, FileText, BarChart3, Shield, ArrowRight } from 'lucide-react'

/**
 * Public home: hero, feature cards, and CTAs to login or dashboard.
 *
 * @returns Landing or welcome-back screen
 */
export const Home = () => {
  const { isAuthenticated, user } = useAuthStore()

  if (isAuthenticated) {
    // If authenticated, redirect to dashboard
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            Welcome back, {user?.name || user?.email}!
          </h1>
          <Link to="/dashboard">
            <Button size="lg">
              Go to Dashboard
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-emerald-50">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <div className="flex justify-center mb-6">
            <div className="rounded-full bg-emerald-100 p-4">
              <Stethoscope className="h-12 w-12 text-emerald-600" />
            </div>
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl mb-4">
            APEX (AI Patient Experience Simulator)
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Advanced medical training platform powered by AI. Practice clinical reasoning,
            receive personalized feedback, and improve your diagnostic skills.
          </p>
          <Link to="/login">
            <Button size="lg" className="text-lg px-8 py-6">
              Get Started
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </Link>
        </div>

        {/* Features Section */}
        <div className="grid gap-8 md:grid-cols-3 mb-16">
          <Card>
            <CardHeader>
              <div className="rounded-lg bg-emerald-100 w-12 h-12 flex items-center justify-center mb-4">
                <FileText className="h-6 w-6 text-emerald-600" />
              </div>
              <CardTitle>Case-Based Learning</CardTitle>
              <CardDescription>
                Practice with real-world medical scenarios and interactive case studies
                designed to enhance your clinical decision-making skills.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <div className="rounded-lg bg-green-100 w-12 h-12 flex items-center justify-center mb-4">
                <BarChart3 className="h-6 w-6 text-green-600" />
              </div>
              <CardTitle>AI-Powered Feedback</CardTitle>
              <CardDescription>
                Receive detailed, personalized feedback on your performance with
                insights into communication, clinical reasoning, and empathy.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <div className="rounded-lg bg-purple-100 w-12 h-12 flex items-center justify-center mb-4">
                <Shield className="h-6 w-6 text-purple-600" />
              </div>
              <CardTitle>Admin Dashboard</CardTitle>
              <CardDescription>
                Comprehensive analytics and monitoring tools for administrators
                to track progress and manage training programs effectively.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>

        {/* CTA Section */}
        <div className="text-center">
          <Card className="bg-emerald-600 text-white border-0">
            <CardHeader>
              <CardTitle className="text-2xl mb-2">Ready to Start Learning?</CardTitle>
              <CardDescription className="text-emerald-100">
                Sign in to access your dashboard and begin your medical training journey.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link to="/login">
                <Button size="lg" variant="secondary" className="w-full sm:w-auto">
                  Sign In to Your Account
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}


