# Authentication & Payment System Implementation Guide

## 🎯 Overview

This document provides detailed implementation instructions for adding user authentication and payment system to the Simply Chrome extension. The implementation ensures that:

1. **Transcript extraction remains free and accessible to all users**
2. **Summary generation requires user authentication**
3. **Free users get 1 video summary per week**
4. **Paid users get unlimited summaries**
5. **User emails are automatically used for summary delivery**

## 📋 Current System Analysis

### ✅ Already Implemented
- Supabase authentication backend (`app/services/auth_service.py`)
- User management with `user_profiles` table
- Quota system with `usage_ledger` tracking  
- Extension state management via Zustand (`extension/simply/store/appStore.ts`)
- Backend authentication middleware (`app/middleware/auth_middleware.py`)
- Row-level security (RLS) policies

### 🎯 What Needs Implementation
- Extension authentication UI components
- Authentication flow in extension
- Summary access control
- Weekly video limit for free users
- Paddle payment integration
- Automatic email integration

---

## 🏗️ Implementation Tasks

## Task 1: Extension Authentication UI Components

### 1.1 Create LoginModal Component

**File:** `extension/simply/components/LoginModal.tsx`

```typescript
import React, { useState } from 'react'
import { useAppStore } from '../store/appStore'

interface LoginModalProps {
  isOpen: boolean
  onClose: () => void
  onSwitchToSignup: () => void
}

export default function LoginModal({ isOpen, onClose, onSwitchToSignup }: LoginModalProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const { setSession, setError: setGlobalError } = useAppStore()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    try {
      // Send login request to background script
      const response = await chrome.runtime.sendMessage({
        type: 'USER_LOGIN',
        data: { email, password }
      })

      if (response.success) {
        // Update session in store
        setSession({
          userId: response.user.id,
          email: response.user.email,
          plan: response.user.plan || 'free',
          isAuthenticated: true,
          supabaseSession: response.session
        })
        onClose()
      } else {
        setError(response.error || 'Login failed')
      }
    } catch (error) {
      setError('Network error. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96 max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Sign In to Simply</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>
        
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          {error && (
            <div className="text-red-600 text-sm">{error}</div>
          )}
          
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>
        
        <div className="mt-4 text-center text-sm">
          <span className="text-gray-600">Don't have an account? </span>
          <button
            onClick={onSwitchToSignup}
            className="text-blue-600 hover:text-blue-700 font-medium"
          >
            Sign Up
          </button>
        </div>
      </div>
    </div>
  )
}
```

### 1.2 Create SignupModal Component

**File:** `extension/simply/components/SignupModal.tsx`

```typescript
import React, { useState } from 'react'
import { useAppStore } from '../store/appStore'

interface SignupModalProps {
  isOpen: boolean
  onClose: () => void
  onSwitchToLogin: () => void
}

export default function SignupModal({ isOpen, onClose, onSwitchToLogin }: SignupModalProps) {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: ''
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const { setSession } = useAppStore()

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      setIsLoading(false)
      return
    }

    try {
      // Send signup request to background script
      const response = await chrome.runtime.sendMessage({
        type: 'USER_SIGNUP',
        data: {
          email: formData.email,
          password: formData.password,
          first_name: formData.firstName,
          last_name: formData.lastName
        }
      })

      if (response.success) {
        // Update session in store
        setSession({
          userId: response.user.id,
          email: response.user.email,
          plan: 'free', // New users start with free plan
          isAuthenticated: true,
          supabaseSession: response.session
        })
        onClose()
      } else {
        setError(response.error || 'Signup failed')
      }
    } catch (error) {
      setError('Network error. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96 max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Create Simply Account</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>
        
        <form onSubmit={handleSignup} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                First Name
              </label>
              <input
                type="text"
                value={formData.firstName}
                onChange={(e) => handleInputChange('firstName', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Last Name
              </label>
              <input
                type="text"
                value={formData.lastName}
                onChange={(e) => handleInputChange('lastName', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => handleInputChange('email', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => handleInputChange('password', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
              minLength={8}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirm Password
            </label>
            <input
              type="password"
              value={formData.confirmPassword}
              onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          {error && (
            <div className="text-red-600 text-sm">{error}</div>
          )}
          
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>
        
        <div className="mt-4 text-center text-sm">
          <span className="text-gray-600">Already have an account? </span>
          <button
            onClick={onSwitchToLogin}
            className="text-blue-600 hover:text-blue-700 font-medium"
          >
            Sign In
          </button>
        </div>
      </div>
    </div>
  )
}
```

### 1.3 Create AuthGuard Component

**File:** `extension/simply/components/AuthGuard.tsx`

```typescript
import React, { useState } from 'react'
import { useSession } from '../store/appStore'
import LoginModal from './LoginModal'
import SignupModal from './SignupModal'

interface AuthGuardProps {
  children: React.ReactNode
  fallback?: React.ReactNode
  requireAuth?: boolean
}

export default function AuthGuard({ children, fallback, requireAuth = true }: AuthGuardProps) {
  const session = useSession()
  const [showLogin, setShowLogin] = useState(false)
  const [showSignup, setShowSignup] = useState(false)

  if (!requireAuth || session.isAuthenticated) {
    return <>{children}</>
  }

  const handleShowLogin = () => {
    setShowSignup(false)
    setShowLogin(true)
  }

  const handleShowSignup = () => {
    setShowLogin(false)
    setShowSignup(true)
  }

  const handleCloseModals = () => {
    setShowLogin(false)
    setShowSignup(false)
  }

  return (
    <>
      {fallback || (
        <div className="text-center p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-800 mb-2">
              Sign in to access summaries
            </h3>
            <p className="text-gray-600 text-sm mb-4">
              Create a free account to get AI-powered video summaries delivered to your email.
            </p>
            <div className="space-y-2">
              <button
                onClick={handleShowLogin}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
              >
                Sign In
              </button>
              <button
                onClick={handleShowSignup}
                className="w-full border border-gray-300 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-50"
              >
                Create Account
              </button>
            </div>
          </div>
        </div>
      )}

      <LoginModal
        isOpen={showLogin}
        onClose={handleCloseModals}
        onSwitchToSignup={handleShowSignup}
      />

      <SignupModal
        isOpen={showSignup}
        onClose={handleCloseModals}
        onSwitchToLogin={handleShowLogin}
      />
    </>
  )
}
```

### 1.4 Create UpgradePrompt Component

**File:** `extension/simply/components/UpgradePrompt.tsx`

```typescript
import React from 'react'
import { useSession } from '../store/appStore'

interface UpgradePromptProps {
  isOpen: boolean
  onClose: () => void
  reason: 'weekly_limit' | 'monthly_limit' | 'quota_exceeded'
}

export default function UpgradePrompt({ isOpen, onClose, reason }: UpgradePromptProps) {
  const session = useSession()

  const getPromptContent = () => {
    switch (reason) {
      case 'weekly_limit':
        return {
          title: 'Weekly Limit Reached',
          message: 'You\'ve used your 1 free video summary this week.',
          benefit: 'Upgrade to get unlimited summaries'
        }
      case 'monthly_limit':
        return {
          title: 'Monthly Limit Reached',
          message: 'You\'ve reached your monthly token limit.',
          benefit: 'Upgrade for higher limits'
        }
      default:
        return {
          title: 'Upgrade Required',
          message: 'You\'ve reached your usage limit.',
          benefit: 'Upgrade for unlimited access'
        }
    }
  }

  const handleUpgrade = async () => {
    try {
      // Send upgrade request to background script
      const response = await chrome.runtime.sendMessage({
        type: 'INITIATE_UPGRADE',
        data: {
          userId: session.userId,
          currentPlan: session.plan
        }
      })

      if (response.success && response.checkoutUrl) {
        // Open Paddle checkout in new tab
        chrome.tabs.create({ url: response.checkoutUrl })
        onClose()
      }
    } catch (error) {
      console.error('Upgrade initiation failed:', error)
    }
  }

  if (!isOpen) return null

  const content = getPromptContent()

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96 max-w-md">
        <div className="text-center">
          <div className="mb-4">
            <div className="mx-auto w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center mb-3">
              <span className="text-yellow-600 text-xl">⭐</span>
            </div>
            <h3 className="text-lg font-semibold text-gray-800 mb-2">
              {content.title}
            </h3>
            <p className="text-gray-600 text-sm mb-4">
              {content.message}
            </p>
          </div>

          <div className="bg-blue-50 rounded-lg p-4 mb-4">
            <h4 className="font-medium text-blue-800 mb-2">Premium Benefits</h4>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>• Unlimited video summaries</li>
              <li>• Priority processing</li>
              <li>• Advanced analytics</li>
              <li>• Email delivery</li>
            </ul>
          </div>

          <div className="space-y-3">
            <button
              onClick={handleUpgrade}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
            >
              Upgrade Now - $9.99/month
            </button>
            <button
              onClick={onClose}
              className="w-full text-gray-600 hover:text-gray-800"
            >
              Maybe Later
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
```

### 1.5 Create QuotaDisplay Component

**File:** `extension/simply/components/QuotaDisplay.tsx`

```typescript
import React from 'react'
import { useSession, useQuota } from '../store/appStore'

export default function QuotaDisplay() {
  const session = useSession()
  const quota = useQuota()

  if (!session.isAuthenticated) return null

  const getUsageColor = (used: number, limit: number) => {
    const percentage = (used / limit) * 100
    if (percentage >= 90) return 'text-red-600 bg-red-100'
    if (percentage >= 70) return 'text-yellow-600 bg-yellow-100'
    return 'text-green-600 bg-green-100'
  }

  const weeklyUsed = session.weeklyVideosUsed || 0
  const weeklyLimit = session.plan === 'free' ? 1 : 999
  const weeklyColor = getUsageColor(weeklyUsed, weeklyLimit)

  return (
    <div className="bg-gray-50 rounded-lg p-3 mb-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">Usage This Week</span>
        <span className={`text-xs px-2 py-1 rounded-full ${weeklyColor}`}>
          {session.plan === 'free' ? 'Free Plan' : 'Premium'}
        </span>
      </div>
      
      <div className="space-y-2">
        <div>
          <div className="flex justify-between text-sm">
            <span>Video Summaries</span>
            <span>{weeklyUsed}/{weeklyLimit === 999 ? '∞' : weeklyLimit}</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${
                weeklyUsed >= weeklyLimit ? 'bg-red-500' : 'bg-blue-500'
              }`}
              style={{
                width: `${Math.min((weeklyUsed / weeklyLimit) * 100, 100)}%`
              }}
            />
          </div>
        </div>

        {session.plan === 'free' && weeklyUsed >= weeklyLimit && (
          <div className="text-xs text-red-600 mt-2">
            Weekly limit reached. Upgrade for unlimited summaries.
          </div>
        )}
      </div>
    </div>
  )
}
```

### 1.6 Add Social OAuth Login (Google & GitHub)

**Why it is critical**  
Adding OAuth dramatically reduces friction during sign-up, increases conversion, and means users do not need to remember another password.

**Files to update / add**
1. **`extension/simply/components/LoginModal.tsx`** – add _Continue with Google_ and _Continue with GitHub_ buttons above the email/password form.
2. **`extension/simply/background.ts`** – import the official Supabase JS client (`@supabase/supabase-js`) and expose a helper `supabase` instance:

```typescript
import { createClient, SupabaseClient } from '@supabase/supabase-js'

const SUPABASE_URL = 'https://<your-project>.supabase.co'
const SUPABASE_ANON_KEY = '<public-anon-key>'
const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    persistSession: false      // we store tokens manually in chrome.storage
  }
})
```

3. **`background.ts` → AUTH HANDLERS** – add:

```typescript
// Social login
if (request.type === 'SOCIAL_LOGIN') {
  supabase.auth.signInWithOAuth({ provider: request.provider, options: { redirectTo: chrome.identity.getRedirectURL() } })
    .then(() => sendResponse({ success: true }))
    .catch(err => sendResponse({ success: false, error: err.message }))
  return true
}
```

4. **`LoginModal.tsx`** – on _Continue with Google_ click:

```typescript
const handleSocialLogin = async (provider: 'google' | 'github') => {
  const res = await chrome.runtime.sendMessage({ type: 'SOCIAL_LOGIN', provider })
  if (!res.success) setError(res.error)
}
```

Buttons:

```tsx
<button onClick={() => handleSocialLogin('google')} className="w-full flex items-center justify-center border border-gray-300 rounded-md py-2 hover:bg-gray-50">
  <img src="/assets/google.svg" className="w-5 h-5 mr-2" /> Continue with Google
</button>
```

5. **`manifest.host_permissions`** – add:
`"https://*.supabase.co/*"`

6. **New environment variables (for extension build)**  
Add to `extension/simply/.env` or build pipeline:

```
VITE_SUPABASE_URL=https://<your-project>.supabase.co
VITE_SUPABASE_ANON_KEY=<public-anon-key>
```

> 🚨 **Security note:** The anon key is public by design; do **not** bundle service-role keys in the extension.

### 1.7 Branding & Modern UX Guidelines (🔥 NEW)

The authentication views must **look and feel like tubevibe.app** so users perceive a single, coherent product.  
Below are non-negotiable UI guidelines.  Tailwind remains the styling engine.

| Category | TubeVibe reference | Extension implementation |
|----------|-------------------|--------------------------|
| **Primary color** | `#FF0050` (rose) | `bg-[#FF0050]`, `text-[#FF0050]` |
| **Accent color**  | `#00C2B8` (teal) | `bg-[#00C2B8]`, `text-[#00C2B8]` |
| **Neutral / bg**  | `#0F0F0F` (very dark grey) | Login/Signup modal outer `<div>` uses `bg-[#0F0F0F]/90` overlay |
| **Font**          | `Inter`, weight 400/600 | Already bundled by Tailwind; add `font-inter` class |
| **Radius**        | 12 px | `rounded-xl` |
| **Shadow**        | Soft, elevation 8 | `shadow-lg shadow-black/30` |
| **Illustration**  | Minimal line-icons | Use heroicons outline for lock / brand icon |
| **Motion**        | 150 ms ease-out | Add `transition-all duration-150` on buttons |

1. **Tailwind Config**  
   Extend colours in `tailwind.config.js`:
   ```js
   theme: {
     extend: {
       colors: {
         tube: {
           primary: '#FF0050',
           accent:  '#00C2B8',
           dark:   '#0F0F0F'
         }
       },
       fontFamily: {
         inter: ['Inter', 'sans-serif']
       }
     }
   }
   ```

2. **Modal Layout**  
   * Centered card with 12 px radius (`rounded-xl`) and soft shadow.  
   * Card width: `max-w-sm` on small screens, `w-96` on desktop.
   * Outer overlay uses `backdrop-blur-sm` for a subtle glass effect.

3. **Component hierarchy**  
   * **Brand bar** at top: TubeVibe icon + word-mark, horizontally centered.  
   * **Social sign-in first** (Google, GitHub) > thin divider > **Email sign-in**.  
   * Single "Continue" button per path; avoid multi-step forms.

4. **Error & success toasts**  
   Display bottom-center toast using `@tailwindcss/typography` friendly colors (`bg-tube-primary/90` for success, `bg-red-600/90` for errors).

5. **Progressive enhancement**  
   * Use `supabase.auth.signInWithOAuth()` pop-up flow (`chrome.identity.launchWebAuthFlow` fallback for MV3).  
   * Email/password fields only visible after user clicks "Use email instead".

6. **Passwordless option (optional MVP+)**  
   TubeVibe uses magic-link login; keep API placeholder: `supabase.auth.signInWithOtp({ email })`.

> 💡  **Design parity test:** take a screenshot of TubeVibe's auth modal at 1366 × 768 and verify your extension modal aligns within ±4 px for: margin-top, font size, button radius, primary colour.

---

## Task 2: Extension Authentication Flow

### 2.1 Update Background Script Authentication

**File:** `extension/simply/background.ts`

**Add to existing file:**

```typescript
// Add authentication handlers to existing background.ts

// Authentication API endpoints
const AUTH_BASE_URL = "https://simply-firy.onrender.com/auth"

// Authentication message handlers
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // ... existing handlers ...

  if (request.type === "USER_LOGIN") {
    handleUserLogin(request.data)
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ success: false, error: error.message }))
    return true
  }

  if (request.type === "USER_SIGNUP") {
    handleUserSignup(request.data)
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ success: false, error: error.message }))
    return true
  }

  if (request.type === "USER_LOGOUT") {
    handleUserLogout()
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ success: false, error: error.message }))
    return true
  }

  if (request.type === "INITIATE_UPGRADE") {
    handleUpgradeInitiation(request.data)
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ success: false, error: error.message }))
    return true
  }

  if (request.type === "CHECK_AUTH_STATUS") {
    checkAuthStatus()
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ success: false, error: error.message }))
    return true
  }
})

// Authentication functions
async function handleUserLogin(credentials: { email: string, password: string }) {
  try {
    const response = await fetch(`${AUTH_BASE_URL}/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(credentials)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Login failed')
    }

    const tokenData = await response.json()
    
    // Store tokens securely
    await storage.set("access_token", tokenData.access_token)
    await storage.set("refresh_token", tokenData.refresh_token)
    
    // Get user info
    const userInfo = await getUserInfo(tokenData.access_token)
    
    return {
      success: true,
      user: userInfo.user,
      session: tokenData
    }
  } catch (error) {
    console.error("Login error:", error)
    return {
      success: false,
      error: error.message
    }
  }
}

async function handleUserSignup(userData: {
  email: string
  password: string
  first_name: string
  last_name: string
}) {
  try {
    const response = await fetch(`${AUTH_BASE_URL}/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(userData)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Signup failed')
    }

    const user = await response.json()
    
    // Auto-login after signup
    const loginResult = await handleUserLogin({
      email: userData.email,
      password: userData.password
    })
    
    return loginResult
  } catch (error) {
    console.error("Signup error:", error)
    return {
      success: false,
      error: error.message
    }
  }
}

async function handleUserLogout() {
  try {
    const accessToken = await storage.get("access_token")
    
    if (accessToken) {
      // Call logout endpoint
      await fetch(`${AUTH_BASE_URL}/logout`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${accessToken}`
        }
      })
    }
    
    // Clear stored tokens
    await storage.remove("access_token")
    await storage.remove("refresh_token")
    await storage.remove("user_info")
    
    return { success: true }
  } catch (error) {
    console.error("Logout error:", error)
    return { success: false, error: error.message }
  }
}

async function getUserInfo(accessToken: string) {
  const response = await fetch(`${AUTH_BASE_URL}/me`, {
    headers: {
      "Authorization": `Bearer ${accessToken}`
    }
  })

  if (!response.ok) {
    throw new Error('Failed to get user info')
  }

  const userInfo = await response.json()
  
  // Store user info
  await storage.set("user_info", userInfo)
  
  return { user: userInfo }
}

async function checkAuthStatus() {
  try {
    const accessToken = await storage.get("access_token")
    
    if (!accessToken) {
      return { success: false, authenticated: false }
    }
    
    // Verify token is still valid
    const userInfo = await getUserInfo(accessToken)
    
    return {
      success: true,
      authenticated: true,
      user: userInfo.user
    }
  } catch (error) {
    // Token invalid, clear storage
    await storage.remove("access_token")
    await storage.remove("refresh_token")
    await storage.remove("user_info")
    
    return { success: false, authenticated: false }
  }
}

async function handleUpgradeInitiation(data: { userId: string, currentPlan: string }) {
  try {
    const accessToken = await storage.get("access_token")
    
    const response = await fetch(`${API_BASE_URL}/paddle/checkout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${accessToken}`
      },
      body: JSON.stringify({
        user_id: data.userId,
        plan: "premium"
      })
    })

    if (!response.ok) {
      throw new Error('Failed to initiate upgrade')
    }

    const result = await response.json()
    
    return {
      success: true,
      checkoutUrl: result.checkout_url
    }
  } catch (error) {
    console.error("Upgrade initiation error:", error)
    return {
      success: false,
      error: error.message
    }
  }
}

// Update existing transcript processing to include auth
async function handleTranscriptProcessing(transcriptData: TranscriptData) {
  try {
    // Check authentication status
    const authStatus = await checkAuthStatus()
    
    if (!authStatus.authenticated) {
      throw new Error('Authentication required for summary generation')
    }
    
    const accessToken = await storage.get("access_token")
    
    // ... existing processing code ...
    
    // Update API call to include authentication
    const result = await submitTranscript({
      ...transcriptData,
      user_id: authStatus.user.id
    }, accessToken)
    
    // ... rest of existing code ...
  } catch (error) {
    console.error("Error processing transcript:", error)
    throw error
  }
}

// Update submitTranscript to include auth token
async function submitTranscript(transcriptData: TranscriptData, accessToken?: string): Promise<any> {
  const idempotencyKey = generateIdempotencyKey(transcriptData.video_id)
  
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Idempotency-Key": idempotencyKey
  }
  
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`
  }
  
  const response = await fetch(`${API_BASE_URL}/yt_ingest`, {
    method: "POST",
    headers,
    body: JSON.stringify(transcriptData)
  })
  
  if (!response.ok) {
    const error = await response.text()
    throw new Error(`API Error: ${response.status} - ${error}`)
  }
  
  const result = await response.json()
  return result
}
```

### 2.2 Update App Store for Authentication

**File:** `extension/simply/store/appStore.ts`

**Update existing interfaces and add authentication methods:**

```typescript
// Update existing UserSession interface
interface UserSession {
  userId?: string
  email?: string
  plan?: 'free' | 'premium' | 'enterprise'
  isAuthenticated: boolean
  supabaseSession?: any
  weeklyVideosUsed?: number
  weeklyLimit?: number
  subscriptionStatus?: 'active' | 'cancelled' | 'expired'
  firstName?: string
  lastName?: string
}

// Update AppState interface to include auth actions
interface AppState {
  // ... existing state properties ...
  
  // Add authentication actions
  login: (credentials: { email: string, password: string }) => Promise<boolean>
  signup: (userData: any) => Promise<boolean>
  logout: () => Promise<void>
  checkAuthStatus: () => Promise<void>
  initializeAuth: () => Promise<void>
}

// Update the store implementation
export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // ... existing state ...

      // Authentication actions
      login: async (credentials) => {
        try {
          const response = await chrome.runtime.sendMessage({
            type: 'USER_LOGIN',
            data: credentials
          })

          if (response.success) {
            set((state) => ({
              session: {
                ...state.session,
                userId: response.user.id,
                email: response.user.email,
                plan: response.user.plan || 'free',
                isAuthenticated: true,
                firstName: response.user.first_name,
                lastName: response.user.last_name,
                supabaseSession: response.session
              }
            }))
            return true
          } else {
            set({ error: response.error })
            return false
          }
        } catch (error) {
          set({ error: 'Network error during login' })
          return false
        }
      },

      signup: async (userData) => {
        try {
          const response = await chrome.runtime.sendMessage({
            type: 'USER_SIGNUP',
            data: userData
          })

          if (response.success) {
            set((state) => ({
              session: {
                ...state.session,
                userId: response.user.id,
                email: response.user.email,
                plan: 'free',
                isAuthenticated: true,
                firstName: response.user.first_name,
                lastName: response.user.last_name,
                supabaseSession: response.session
              }
            }))
            return true
          } else {
            set({ error: response.error })
            return false
          }
        } catch (error) {
          set({ error: 'Network error during signup' })
          return false
        }
      },

      logout: async () => {
        try {
          await chrome.runtime.sendMessage({ type: 'USER_LOGOUT' })
          
          set((state) => ({
            session: {
              ...defaultSession,
              isAuthenticated: false
            },
            quota: defaultQuota,
            currentVideo: null,
            recentVideos: []
          }))
        } catch (error) {
          console.error('Logout error:', error)
        }
      },

      checkAuthStatus: async () => {
        try {
          const response = await chrome.runtime.sendMessage({
            type: 'CHECK_AUTH_STATUS'
          })

          if (response.success && response.authenticated) {
            set((state) => ({
              session: {
                ...state.session,
                userId: response.user.id,
                email: response.user.email,
                plan: response.user.plan || 'free',
                isAuthenticated: true,
                firstName: response.user.first_name,
                lastName: response.user.last_name
              }
            }))
          } else {
            set((state) => ({
              session: {
                ...defaultSession,
                isAuthenticated: false
              }
            }))
          }
        } catch (error) {
          console.error('Auth status check failed:', error)
          set((state) => ({
            session: {
              ...defaultSession,
              isAuthenticated: false
            }
          }))
        }
      },

      initializeAuth: async () => {
        const state = get()
        if (!state.session.isAuthenticated) {
          await state.checkAuthStatus()
        }
      },

      // Update canProcessVideo to check authentication and weekly limits
      canProcessVideo: () => {
        const state = get()
        const { session, quota } = state
        
        // Must be authenticated for summary generation
        if (!session.isAuthenticated) {
          return false
        }
        
        // Check weekly video limit for free users
        if (session.plan === 'free') {
          const weeklyUsed = session.weeklyVideosUsed || 0
          if (weeklyUsed >= 1) {
            return false
          }
        }
        
        // Check daily request limit
        if (quota.dailyRequests >= quota.dailyLimit) {
          return false
        }
        
        // Check monthly token limit
        if (quota.monthlyTokens + 5000 > quota.monthlyLimit) {
          return false
        }
        
        return true
      }

      // ... rest of existing methods ...
    }),
    {
      // ... existing persist config ...
      
      // Initialize auth on store creation
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.initializeAuth()
        }
      }
    }
  )
)

// Add new selectors for authentication
export const useAuth = () => useAppStore((state) => ({
  session: state.session,
  login: state.login,
  signup: state.signup,
  logout: state.logout,
  checkAuthStatus: state.checkAuthStatus
}))
```

---

## Task 3: Backend Authentication Enforcement

### 3.1 Update YouTube Routes for Authentication

**File:** `app/routes/youtube_routes.py`

**Replace the test endpoint with authenticated endpoint:**

```python
# Remove or modify the yt_test_ingest endpoint to require authentication
@router.post("/yt_ingest", response_model=YouTubeIngestResponse)
async def ingest_youtube_transcript(
    request: YouTubeIngestRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: Dict = Depends(get_current_user)  # Now required, not optional
):
    """
    Ingest YouTube transcript from Chrome extension (requires authentication)
    
    Features:
    - User authentication required
    - Weekly video limit for free users
    - Quota validation and enforcement
    - Automatic email delivery to authenticated user
    """
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Use authenticated user's ID instead of request user_id
        user_id = current_user["id"]
        user_email = current_user["email"]
        user_plan = current_user.get("user_metadata", {}).get("plan", "free")
        
        logger.info(f"Processing request for authenticated user: {user_email} (Plan: {user_plan})")
        
        # Check weekly video limit for free users
        if user_plan == "free":
            can_process_weekly = await check_weekly_video_limit(user_id)
            if not can_process_weekly:
                raise HTTPException(
                    status_code=402,
                    detail="Weekly video limit reached. You can process 1 video per week on the free plan. Upgrade to Premium for unlimited videos."
                )
        
        # Calculate transcript hash for duplicate detection
        transcript_hash = get_transcript_hash(request.transcript)
        
        # Handle idempotency
        if idempotency_key:
            stored_response = get_idempotency_result(idempotency_key)
            if stored_response:
                logger.info(f"Duplicate request detected: {idempotency_key}")
                return YouTubeIngestResponse(
                    success=True,
                    job_id=stored_response["job_id"],
                    message="Duplicate request - returning cached response",
                    duplicate=True,
                    estimated_tokens=stored_response["estimated_tokens"],
                    video_id=request.video_id
                )
        else:
            idempotency_key = generate_idempotency_key(
                request.video_id, 
                user_id, 
                transcript_hash
            )
        
        # Estimate tokens
        estimated_tokens = estimate_tokens(request.transcript)
        logger.info(f"Estimated tokens for video {request.video_id}: {estimated_tokens}")
        
        # Check quota limits
        can_process, quota_message = await check_quota_limits(
            user_id, 
            estimated_tokens, 
            request.duration
        )
        if not can_process:
            raise HTTPException(
                status_code=429, 
                detail=quota_message
            )
        
        # Validate request
        if not request.transcript.strip():
            raise HTTPException(status_code=400, detail="Transcript cannot be empty")
        
        if len(request.transcript) > 1_000_000:  # 1MB limit
            raise HTTPException(status_code=413, detail="Transcript too large")
        
        # Save transcript to storage
        storage_path = await save_transcript_to_storage(request, job_id)
        
        # Process using the full BPT pipeline
        from app.services.ingestion_service import IngestionService
        
        ingestion_service = IngestionService()
        transcript_id = f"yt_{request.video_id}_{job_id[:8]}"
        
        # Prepare metadata for the pipeline
        pipeline_metadata = {
            "source": "youtube_extension",
            "job_id": job_id,
            "video_url": f"https://youtube.com/watch?v={request.video_id}",
            "processing_type": "youtube_transcript",
            "channel_name": request.channel_name,
            "duration": request.duration,
            "user_id": user_id,
            "user_email": user_email,  # Add user email for automatic delivery
            "user_plan": user_plan,
            "original_source": request.source,
            "ingestion_timestamp": datetime.utcnow().isoformat()
        }
        
        if request.metadata:
            pipeline_metadata.update(request.metadata)
        
        # Process using the existing BPT ingestion pipeline
        result = await ingestion_service.start_ingestion_pipeline_with_text(
            transcript_id=transcript_id,
            transcript_text=request.transcript,
            meeting_title=f"[YouTube] {request.title}",
            meeting_date=datetime.utcnow().isoformat(),
            metadata=pipeline_metadata
        )
        
        if not result.get("success"):
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"❌ Pipeline processing failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {error_msg}")
        
        logger.info(f"✅ Full pipeline processing completed for job {job_id}")
        
        # Increment weekly video usage for free users
        if user_plan == "free":
            await increment_weekly_video_usage(user_id)
        
        # Store idempotency response
        response_data = {
            "job_id": job_id,
            "estimated_tokens": estimated_tokens,
            "created_at": datetime.utcnow().isoformat()
        }
        store_idempotency_result(idempotency_key, response_data, ttl=86400)
        
        logger.info(f"Successfully processed YouTube transcript for user: {user_email}")
        
        return YouTubeIngestResponse(
            success=True,
            job_id=job_id,
            message=f"YouTube transcript processed! Summary will be delivered to {user_email}. Transcript ID: {transcript_id}",
            duplicate=False,
            estimated_tokens=estimated_tokens,
            video_id=request.video_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in yt_ingest: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Add new functions for weekly limit checking
async def check_weekly_video_limit(user_id: str) -> bool:
    """Check if user can process another video this week"""
    try:
        from app.services.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Call the database function
        result = supabase.rpc('can_process_weekly_video', {'user_uuid': user_id}).execute()
        
        return bool(result.data) if result.data is not None else False
        
    except Exception as e:
        logger.error(f"Error checking weekly video limit for user {user_id}: {e}")
        return False

async def increment_weekly_video_usage(user_id: str) -> bool:
    """Increment user's weekly video usage count"""
    try:
        from app.services.quota_service import quota_service
        
        # Use existing quota service to increment video processing
        success = await quota_service.increment_usage(
            user_id=user_id,
            tokens_consumed=0,
            requests_increment=0,
            videos_increment=1
        )
        
        return success
        
    except Exception as e:
        logger.error(f"Error incrementing weekly video usage for user {user_id}: {e}")
        return False
```

### 3.2 Add Database Function for Weekly Limits

**File:** `scripts/migration/add_weekly_video_limits.sql`

```sql
-- Add weekly video limit function
CREATE OR REPLACE FUNCTION public.can_process_weekly_video(user_uuid UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    user_limits JSONB;
    weekly_count INTEGER;
    weekly_limit INTEGER;
    user_plan TEXT;
BEGIN
    -- Get user plan and limits
    SELECT plan_limits, plan_type INTO user_limits, user_plan
    FROM user_profiles 
    WHERE user_id = user_uuid;
    
    -- Default weekly limit based on plan
    IF user_plan = 'free' THEN
        weekly_limit := 1;
    ELSE
        weekly_limit := 999; -- Unlimited for paid plans
    END IF;
    
    -- Override with custom limit if set
    IF user_limits IS NOT NULL AND user_limits ? 'weekly_videos' THEN
        weekly_limit := (user_limits->>'weekly_videos')::INTEGER;
    END IF;
    
    -- Count videos processed this week
    SELECT COUNT(*) INTO weekly_count
    FROM usage_ledger 
    WHERE user_id = user_uuid 
    AND resource_type = 'video_processing'
    AND created_at >= date_trunc('week', NOW());
    
    RETURN weekly_count < weekly_limit;
END;
$$;

-- Add function to get weekly usage stats
CREATE OR REPLACE FUNCTION public.get_weekly_video_usage(user_uuid UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    user_limits JSONB;
    weekly_count INTEGER;
    weekly_limit INTEGER;
    user_plan TEXT;
    week_start DATE;
    week_end DATE;
BEGIN
    -- Get user plan and limits
    SELECT plan_limits, plan_type INTO user_limits, user_plan
    FROM user_profiles 
    WHERE user_id = user_uuid;
    
    -- Default weekly limit based on plan
    IF user_plan = 'free' THEN
        weekly_limit := 1;
    ELSE
        weekly_limit := 999; -- Unlimited for paid plans
    END IF;
    
    -- Override with custom limit if set
    IF user_limits IS NOT NULL AND user_limits ? 'weekly_videos' THEN
        weekly_limit := (user_limits->>'weekly_videos')::INTEGER;
    END IF;
    
    -- Calculate week boundaries
    week_start := date_trunc('week', NOW())::DATE;
    week_end := (date_trunc('week', NOW()) + interval '6 days')::DATE;
    
    -- Count videos processed this week
    SELECT COUNT(*) INTO weekly_count
    FROM usage_ledger 
    WHERE user_id = user_uuid 
    AND resource_type = 'video_processing'
    AND created_at >= week_start;
    
    RETURN json_build_object(
        'videos_used', weekly_count,
        'videos_limit', weekly_limit,
        'week_start', week_start,
        'week_end', week_end,
        'can_process', weekly_count < weekly_limit,
        'plan', user_plan
    )::jsonb;
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION public.can_process_weekly_video(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_weekly_video_usage(UUID) TO authenticated;

-- Update user_profiles table to include weekly limits in default plan_limits
UPDATE public.user_profiles 
SET plan_limits = plan_limits || '{"weekly_videos": 1}'::jsonb
WHERE plan_type = 'free' OR plan_type IS NULL;

UPDATE public.user_profiles 
SET plan_limits = plan_limits || '{"weekly_videos": 999}'::jsonb
WHERE plan_type IN ('premium', 'enterprise');
```

---

## Task 4: Paddle Payment Integration

### 4.1 Add Paddle Routes

**File:** `app/routes/paddle_routes.py`

```python
from fastapi import APIRouter, HTTPException, Request, Depends
import logging
import os
import hashlib
import hmac
from typing import Dict, Any
from urllib.parse import parse_qs
import json

from app.middleware.auth_middleware import get_current_user
from app.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/paddle", tags=["payments"])

# Paddle configuration
PADDLE_VENDOR_ID = os.getenv("PADDLE_VENDOR_ID")
PADDLE_API_KEY = os.getenv("PADDLE_API_KEY")
PADDLE_PUBLIC_KEY = os.getenv("PADDLE_PUBLIC_KEY")
PADDLE_WEBHOOK_SECRET = os.getenv("PADDLE_WEBHOOK_SECRET")
PADDLE_ENVIRONMENT = os.getenv("PADDLE_ENVIRONMENT", "sandbox")  # sandbox or production

@router.post("/checkout")
async def create_checkout_session(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a Paddle checkout session for user upgrade
    """
    try:
        data = await request.json()
        user_id = current_user["id"]
        user_email = current_user["email"]
        plan = data.get("plan", "premium")
        
        # Paddle checkout URL (you'll need to replace with your actual product ID)
        product_id = "pro_01234567890" if plan == "premium" else "pro_01234567891"
        
        checkout_url = (
            f"https://checkout.paddle.com/checkout?"
            f"vendor={PADDLE_VENDOR_ID}&"
            f"product={product_id}&"
            f"email={user_email}&"
            f"passthrough={user_id}&"
            f"success_url=https://simply.io/success&"
            f"cancel_url=https://simply.io/cancel"
        )
        
        logger.info(f"Created checkout session for user {user_email}: {checkout_url}")
        
        return {
            "success": True,
            "checkout_url": checkout_url,
            "product_id": product_id
        }
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail=f"Checkout creation failed: {str(e)}")

@router.post("/webhook")
async def handle_paddle_webhook(request: Request):
    """
    Handle Paddle webhook events for subscription updates
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Verify webhook signature
        if not verify_paddle_webhook(body, request.headers):
            logger.warning("Invalid Paddle webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Parse form data
        form_data = parse_qs(body.decode('utf-8'))
        
        # Extract event data
        alert_name = form_data.get('alert_name', [''])[0]
        user_id = form_data.get('passthrough', [''])[0]
        
        logger.info(f"Received Paddle webhook: {alert_name} for user {user_id}")
        
        if alert_name == "subscription_payment_succeeded":
            await handle_subscription_payment_success(form_data)
        elif alert_name == "subscription_created":
            await handle_subscription_created(form_data)
        elif alert_name == "subscription_cancelled":
            await handle_subscription_cancelled(form_data)
        elif alert_name == "subscription_payment_failed":
            await handle_subscription_payment_failed(form_data)
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error processing Paddle webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

def verify_paddle_webhook(body: bytes, headers: Dict[str, str]) -> bool:
    """
    Verify Paddle webhook signature
    """
    try:
        signature = headers.get('paddle-signature', '')
        
        if not signature or not PADDLE_WEBHOOK_SECRET:
            return False
        
        # Parse signature
        sig_parts = {}
        for part in signature.split(','):
            key, value = part.split('=', 1)
            sig_parts[key] = value
        
        timestamp = sig_parts.get('ts', '')
        signature_hash = sig_parts.get('h1', '')
        
        # Create expected signature
        message = f"{timestamp}.{body.decode('utf-8')}"
        expected_signature = hmac.new(
            PADDLE_WEBHOOK_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature_hash, expected_signature)
        
    except Exception as e:
        logger.error(f"Error verifying Paddle webhook signature: {e}")
        return False

async def handle_subscription_payment_success(form_data: Dict[str, list]):
    """
    Handle successful subscription payment
    """
    try:
        user_id = form_data.get('passthrough', [''])[0]
        subscription_id = form_data.get('subscription_id', [''])[0]
        
        if not user_id:
            logger.error("No user ID in webhook data")
            return
        
        # Update user to premium plan
        await upgrade_user_plan(user_id, "premium", subscription_id)
        
        logger.info(f"Successfully upgraded user {user_id} to premium")
        
    except Exception as e:
        logger.error(f"Error handling subscription payment success: {e}")

async def handle_subscription_created(form_data: Dict[str, list]):
    """
    Handle new subscription creation
    """
    try:
        user_id = form_data.get('passthrough', [''])[0]
        subscription_id = form_data.get('subscription_id', [''])[0]
        
        if not user_id:
            logger.error("No user ID in webhook data")
            return
        
        # Update user to premium plan
        await upgrade_user_plan(user_id, "premium", subscription_id)
        
        logger.info(f"Successfully created subscription for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling subscription creation: {e}")

async def handle_subscription_cancelled(form_data: Dict[str, list]):
    """
    Handle subscription cancellation
    """
    try:
        user_id = form_data.get('passthrough', [''])[0]
        
        if not user_id:
            logger.error("No user ID in webhook data")
            return
        
        # Downgrade user to free plan
        await downgrade_user_plan(user_id)
        
        logger.info(f"Successfully cancelled subscription for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling subscription cancellation: {e}")

async def handle_subscription_payment_failed(form_data: Dict[str, list]):
    """
    Handle failed subscription payment
    """
    try:
        user_id = form_data.get('passthrough', [''])[0]
        
        if not user_id:
            logger.error("No user ID in webhook data")
            return
        
        # Mark subscription as payment failed (but don't downgrade immediately)
        # You might want to implement a grace period
        logger.warning(f"Payment failed for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling subscription payment failure: {e}")

async def upgrade_user_plan(user_id: str, plan: str, subscription_id: str):
    """
    Upgrade user to premium plan
    """
    try:
        supabase = get_supabase_client()
        
        # Premium plan limits
        premium_limits = {
            "monthly_tokens": 200000,
            "daily_requests": 1000,
            "weekly_videos": 999,  # Unlimited
            "max_video_duration": 7200,
            "tier": "premium"
        }
        
        # Update user profile
        supabase.table("user_profiles").update({
            "plan_type": plan,
            "plan_limits": premium_limits,
            "subscription_status": "active",
            "subscription_id": subscription_id,
            "updated_at": "now()"
        }).eq("user_id", user_id).execute()
        
        logger.info(f"Upgraded user {user_id} to {plan} plan")
        
    except Exception as e:
        logger.error(f"Error upgrading user plan: {e}")
        raise

async def downgrade_user_plan(user_id: str):
    """
    Downgrade user to free plan
    """
    try:
        supabase = get_supabase_client()
        
        # Free plan limits
        free_limits = {
            "monthly_tokens": 50000,
            "daily_requests": 100,
            "weekly_videos": 1,
            "max_video_duration": 3600,
            "tier": "free"
        }
        
        # Update user profile
        supabase.table("user_profiles").update({
            "plan_type": "free",
            "plan_limits": free_limits,
            "subscription_status": "cancelled",
            "updated_at": "now()"
        }).eq("user_id", user_id).execute()
        
        logger.info(f"Downgraded user {user_id} to free plan")
        
    except Exception as e:
        logger.error(f"Error downgrading user plan: {e}")
        raise

@router.get("/subscription/{user_id}")
async def get_subscription_status(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get user's subscription status
    """
    try:
        # Verify user can access this info
        if current_user["id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        supabase = get_supabase_client()
        
        result = supabase.table("user_profiles").select(
            "plan_type, subscription_status, plan_limits"
        ).eq("user_id", user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = result.data[0]
        
        return {
            "plan": user_data.get("plan_type", "free"),
            "status": user_data.get("subscription_status", "inactive"),
            "limits": user_data.get("plan_limits", {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving subscription: {str(e)}")
```

### 4.2 Update Main Router

**File:** `app/routes/__init__.py`

```python
# Add paddle router to existing imports
from .paddle_routes import router as paddle_router

# Add to existing router includes
api_router.include_router(paddle_router)
```

---

## Task 5: Update Extension UI for Authentication

### 5.1 Update Popup Component

**File:** `extension/simply/popup.tsx`

**Add authentication integration to existing popup:**

```typescript
// Add imports at the top
import AuthGuard from "./components/AuthGuard"
import UpgradePrompt from "./components/UpgradePrompt"
import QuotaDisplay from "./components/QuotaDisplay"
import { useAuth } from "./store/appStore"

// Update the IndexPopup function
function IndexPopup() {
  // ... existing state and hooks ...
  
  // Add authentication hooks
  const { session, logout } = useAuth()
  const [showUpgradePrompt, setShowUpgradePrompt] = useState(false)
  const [upgradeReason, setUpgradeReason] = useState<'weekly_limit' | 'monthly_limit' | 'quota_exceeded'>('weekly_limit')

  // ... existing useEffect and functions ...

  // Update sendToBackend function to handle authentication
  const sendToBackend = async () => {
    if (!videoData) {
      alert('No transcript data available')
      return
    }

    // Check authentication first
    if (!session.isAuthenticated) {
      setError('Please sign in to generate summaries')
      return
    }

    // Check quota before processing
    if (!canProcessVideo()) {
      if (session.plan === 'free' && (session.weeklyVideosUsed || 0) >= 1) {
        setUpgradeReason('weekly_limit')
        setShowUpgradePrompt(true)
        return
      } else {
        setError('Quota exceeded. Please upgrade your plan or wait for quota reset.')
        return
      }
    }

    clearError()
    setLoading(true)
    setAwaitingSummary(true)
    
    // ... rest of existing sendToBackend logic ...
  }

  // Add user menu component
  const UserMenu = () => {
    const [showMenu, setShowMenu] = useState(false)

    if (!session.isAuthenticated) return null

    return (
      <div className="relative">
        <button
          onClick={() => setShowMenu(!showMenu)}
          className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100"
        >
          <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm">
            {session.firstName?.[0] || session.email?.[0] || 'U'}
          </div>
          <span className="text-sm font-medium">{session.firstName || session.email}</span>
        </button>

        {showMenu && (
          <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border z-50">
            <div className="p-2">
              <div className="px-3 py-2 text-sm text-gray-500">
                {session.email}
              </div>
              <div className="px-3 py-1 text-xs text-gray-400">
                {session.plan === 'free' ? 'Free Plan' : 'Premium Plan'}
              </div>
              <hr className="my-2" />
              <button
                onClick={() => {
                  logout()
                  setShowMenu(false)
                }}
                className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded"
              >
                Sign Out
              </button>
            </div>
          </div>
        )}
      </div>
    )
  }

  // Update the render method
  return (
    <ErrorBoundary>
      <div className="w-[400px] h-[600px] bg-white">
        {/* Header with user menu */}
        <div className="flex items-center justify-between p-4 border-b">
          <h1 className="text-lg font-semibold">Simply</h1>
          <UserMenu />
        </div>

        {/* Show quota display for authenticated users */}
        {session.isAuthenticated && <QuotaDisplay />}

        {/* Existing tab navigation */}
        <div className="flex border-b">
          {/* ... existing tab buttons ... */}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'transcript' && (
            <div className="h-full p-4">
              {/* Transcript tab content - no auth required */}
              {/* ... existing transcript content ... */}
            </div>
          )}

          {activeTab === 'summary' && (
            <div className="h-full">
              <AuthGuard>
                <div className="p-4">
                  {/* Existing summary content */}
                  {/* ... existing summary content ... */}
                </div>
              </AuthGuard>
            </div>
          )}

          {activeTab === 'chat' && (
            <div className="h-full">
              <AuthGuard>
                {/* Existing chat content */}
                {/* ... existing chat content ... */}
              </AuthGuard>
            </div>
          )}
        </div>

        {/* Upgrade prompt modal */}
        <UpgradePrompt
          isOpen={showUpgradePrompt}
          onClose={() => setShowUpgradePrompt(false)}
          reason={upgradeReason}
        />

        {/* ... existing modals and components ... */}
      </div>
    </ErrorBoundary>
  )
}
```

### 5.2 Update Content Script for User Context

**File:** `extension/simply/content.ts`

**Add user context to existing content script:**

```typescript
// Add to existing class
class YouTubeTranscriptExtractor {
  // ... existing properties ...
  
  private async generateSummary(transcript: string): Promise<void> {
    if (!this.panel) return
    
    const summaryTab = this.panel.querySelector('#simply-summary-tab') as HTMLElement
    this.showSkeletonLoader(summaryTab)
    
    try {
      // Check authentication status first
      const authResponse = await chrome.runtime.sendMessage({
        type: "CHECK_AUTH_STATUS"
      })

      if (!authResponse.authenticated) {
        this.hideSkeletonLoader(summaryTab)
        this.displayAuthRequired(summaryTab)
        return
      }

      // Calculate transcript length
      const wordCount = transcript.split(' ').length
      const readingTime = Math.ceil(wordCount / 200)
      const transcriptLength = `${wordCount} words (~${readingTime} min read)`
      
      // Send transcript to background script for processing
      const response = await chrome.runtime.sendMessage({
        type: "PROCESS_TRANSCRIPT",
        data: {
          video_id: this.metadata?.videoId || '',
          title: this.metadata?.title || 'Unknown Title',
          channel_name: this.metadata?.channelName || 'Unknown Channel',
          duration: this.metadata?.duration ? this.parseDurationToSeconds(this.metadata.duration) : 0,
          transcript: transcript,
          source: "chrome_extension",
          metadata: {
            ...this.metadata,
            transcript_length: transcriptLength
          }
        }
      })
      
      if (response.success) {
        this.hideSkeletonLoader(summaryTab)
        this.displaySummaryResults(summaryTab, response.data, transcript)
        this.showToast('Summary generated successfully!', 'success')
      } else {
        throw new Error(response.error || 'Unknown error')
      }
      
    } catch (error) {
      console.error('Summary generation failed:', error)
      this.hideSkeletonLoader(summaryTab)
      this.displayError(summaryTab, error instanceof Error ? error.message : 'Summary generation failed')
      this.showToast('Summary generation failed', 'error')
    }
  }

  private displayAuthRequired(container: HTMLElement): void {
    container.innerHTML = `
      <div class="simply-auth-required">
        <div class="simply-auth-content">
          <div class="simply-auth-icon">🔒</div>
          <h3>Sign in Required</h3>
          <p>Please sign in to your Simply account to generate AI-powered summaries.</p>
          <button class="simply-auth-button" id="simply-open-popup">
            Open Simply Extension
          </button>
        </div>
      </div>
    `

    // Add click handler for the button
    const openButton = container.querySelector('#simply-open-popup') as HTMLButtonElement
    openButton?.addEventListener('click', () => {
      // Open the extension popup
      chrome.runtime.sendMessage({ type: 'OPEN_POPUP' })
    })
  }

  // ... rest of existing methods ...
}
```

---

## Task 6: Email Integration Update

### 6.1 Update Ingestion Service for Automatic Email

**File:** `app/services/ingestion_service.py`

**Update the email sending logic to use authenticated user's email:**

```python
# Update the existing _send_summary_email method
async def _send_summary_email(self, transcript_id: str, title: str, summary: str, trades: List[Dict[str, Any]], user_email: str = None) -> bool:
    """
    Send summary email to user
    Now uses authenticated user's email automatically
    """
    try:
        if not user_email:
            logger.warning(f"No user email provided for transcript {transcript_id}")
            return False

        # Use existing email service
        if self.email_service and self.email_service.is_configured:
            logger.info(f"Sending summary email to authenticated user: {user_email}")
            
            # Prepare video data
            video_data = {
                "title": title,
                "video_id": transcript_id.replace("yt_", "").split("_")[0] if transcript_id.startswith("yt_") else "unknown",
                "url": f"https://youtube.com/watch?v={transcript_id.replace('yt_', '').split('_')[0]}" if transcript_id.startswith("yt_") else "#"
            }
            
            result = await self.email_service.send_youtube_summary_email(
                recipient_email=user_email,
                video_data=video_data,
                summary=summary
            )
            
            if result.get("success"):
                logger.info(f"✅ Summary email sent successfully to {user_email}")
                return True
            else:
                logger.error(f"❌ Failed to send summary email: {result.get('error')}")
                return False
        else:
            logger.warning("Email service not configured")
            return False
            
    except Exception as e:
        logger.error(f"Error sending summary email: {str(e)}")
        return False

# Update the pipeline to pass user email
async def start_ingestion_pipeline_with_text(
    self,
    transcript_id: str,
    transcript_text: str,
    meeting_title: str,
    meeting_date: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Enhanced pipeline that automatically sends email to authenticated users
    """
    try:
        # ... existing pipeline logic ...
        
        # Extract user email from metadata
        user_email = metadata.get("user_email") if metadata else None
        
        # ... existing processing steps ...
        
        # Step 6: Send email notification (now automatic for authenticated users)
        if user_email and summary_html:
            logger.info(f"📧 Sending automatic email notification to authenticated user: {user_email}")
            email_sent = await self._send_summary_email(
                transcript_id=transcript_id,
                title=meeting_title,
                summary=summary_html,
                trades=extracted_trades,
                user_email=user_email
            )
            
            if email_sent:
                steps_completed.append("send_email")
                logger.info(f"✅ Email automatically sent to {user_email}")
            else:
                logger.warning(f"⚠️ Email sending failed for {user_email}")
        else:
            logger.info("📧 No user email provided, skipping email notification")
        
        # ... rest of existing pipeline logic ...
        
    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}")
        return {"success": False, "error": str(e)}
```

---

## Task 7: Environment Variables and Configuration

### 7.1 Update Environment Configuration

**File:** `.env.example`

```bash
# Existing environment variables...

# Paddle Payment Configuration
PADDLE_VENDOR_ID=your_paddle_vendor_id
PADDLE_API_KEY=your_paddle_api_key
PADDLE_PUBLIC_KEY=your_paddle_public_key
PADDLE_WEBHOOK_SECRET=your_paddle_webhook_secret
PADDLE_ENVIRONMENT=sandbox  # or production

# Authentication Configuration (already exists)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# Email Configuration (already exists)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### 7.2 Update Extension Manifest Permissions

**File:** `extension/simply/package.json`

```json
{
  "manifest": {
    "host_permissions": [
      "https://www.youtube.com/*",
      "https://m.youtube.com/*",
      "https://*.googlevideo.com/*",
      "https://localhost:8000/*",
      "http://localhost:8000/*",
      "https://simply-firy.onrender.com/*",
      "https://*.youtube.com/*",
      "https://checkout.paddle.com/*",
      "https://simply.io/*"
    ],
    "permissions": [
      "storage",
      "activeTab",
      "scripting",
      "sidePanel",
      "webRequest",
      "tabs"
    ]
  }
}
```

---

## Task 8: Testing and Validation

### 8.1 Create Test Script

**File:** `scripts/test_auth_flow.py`

```python
"""
Test script for authentication and payment flow
"""
import asyncio
import aiohttp
import json
import os
from datetime import datetime

BASE_URL = "http://localhost:8000"  # or your production URL

async def test_auth_flow():
    """Test the complete authentication flow"""
    
    async with aiohttp.ClientSession() as session:
        # Test 1: User Registration
        print("🧪 Testing user registration...")
        register_data = {
            "email": f"test_{datetime.now().timestamp()}@example.com",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        async with session.post(f"{BASE_URL}/auth/register", json=register_data) as resp:
            if resp.status == 201:
                print("✅ Registration successful")
                user_data = await resp.json()
                print(f"   User ID: {user_data['id']}")
            else:
                print(f"❌ Registration failed: {resp.status}")
                return
        
        # Test 2: User Login
        print("\n🧪 Testing user login...")
        login_data = {
            "email": register_data["email"],
            "password": register_data["password"]
        }
        
        async with session.post(f"{BASE_URL}/auth/login", json=login_data) as resp:
            if resp.status == 200:
                print("✅ Login successful")
                token_data = await resp.json()
                access_token = token_data["access_token"]
                print(f"   Access token received")
            else:
                print(f"❌ Login failed: {resp.status}")
                return
        
        # Test 3: Authenticated Request to YouTube Endpoint
        print("\n🧪 Testing authenticated YouTube request...")
        headers = {"Authorization": f"Bearer {access_token}"}
        youtube_data = {
            "video_id": "test123",
            "title": "Test Video",
            "channel_name": "Test Channel",
            "duration": 300,
            "transcript": "This is a test transcript for authentication testing.",
            "user_id": user_data["id"],
            "source": "test"
        }
        
        async with session.post(f"{BASE_URL}/api/yt_ingest", json=youtube_data, headers=headers) as resp:
            if resp.status == 200:
                print("✅ Authenticated YouTube request successful")
                result = await resp.json()
                print(f"   Job ID: {result['job_id']}")
            else:
                print(f"❌ YouTube request failed: {resp.status}")
                error = await resp.text()
                print(f"   Error: {error}")
        
        # Test 4: Weekly Limit Check (second request should fail for free users)
        print("\n🧪 Testing weekly limit enforcement...")
        async with session.post(f"{BASE_URL}/api/yt_ingest", json=youtube_data, headers=headers) as resp:
            if resp.status == 402:
                print("✅ Weekly limit enforcement working")
                error = await resp.json()
                print(f"   Expected error: {error['detail']}")
            else:
                print(f"⚠️ Weekly limit not enforced: {resp.status}")
        
        # Test 5: User Info
        print("\n🧪 Testing user info endpoint...")
        async with session.get(f"{BASE_URL}/auth/me", headers=headers) as resp:
            if resp.status == 200:
                print("✅ User info endpoint working")
                user_info = await resp.json()
                print(f"   Email: {user_info['email']}")
                print(f"   Plan: {user_info.get('role', 'free')}")
            else:
                print(f"❌ User info failed: {resp.status}")

if __name__ == "__main__":
    asyncio.run(test_auth_flow())
```

### 8.2 Create Extension Test

**File:** `extension/simply/test_auth.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>Simply Extension Auth Test</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .test-section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
        .success { color: green; }
        .error { color: red; }
        .info { color: blue; }
        button { padding: 10px 15px; margin: 5px; }
    </style>
</head>
<body>
    <h1>Simply Extension Authentication Test</h1>
    
    <div class="test-section">
        <h3>Authentication Status</h3>
        <div id="auth-status">Checking...</div>
        <button onclick="checkAuthStatus()">Refresh Status</button>
    </div>
    
    <div class="test-section">
        <h3>Test Login</h3>
        <input type="email" id="email" placeholder="Email" />
        <input type="password" id="password" placeholder="Password" />
        <button onclick="testLogin()">Login</button>
        <div id="login-result"></div>
    </div>
    
    <div class="test-section">
        <h3>Test Transcript Processing</h3>
        <button onclick="testTranscriptProcessing()">Process Test Video</button>
        <div id="processing-result"></div>
    </div>
    
    <div class="test-section">
        <h3>Test Logout</h3>
        <button onclick="testLogout()">Logout</button>
        <div id="logout-result"></div>
    </div>

    <script>
        async function checkAuthStatus() {
            const statusDiv = document.getElementById('auth-status');
            try {
                const response = await chrome.runtime.sendMessage({
                    type: 'CHECK_AUTH_STATUS'
                });
                
                if (response.authenticated) {
                    statusDiv.innerHTML = `<span class="success">✅ Authenticated as ${response.user.email}</span>`;
                } else {
                    statusDiv.innerHTML = `<span class="error">❌ Not authenticated</span>`;
                }
            } catch (error) {
                statusDiv.innerHTML = `<span class="error">Error: ${error.message}</span>`;
            }
        }
        
        async function testLogin() {
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const resultDiv = document.getElementById('login-result');
            
            if (!email || !password) {
                resultDiv.innerHTML = '<span class="error">Please enter email and password</span>';
                return;
            }
            
            try {
                const response = await chrome.runtime.sendMessage({
                    type: 'USER_LOGIN',
                    data: { email, password }
                });
                
                if (response.success) {
                    resultDiv.innerHTML = `<span class="success">✅ Login successful</span>`;
                    checkAuthStatus();
                } else {
                    resultDiv.innerHTML = `<span class="error">❌ Login failed: ${response.error}</span>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<span class="error">Error: ${error.message}</span>`;
            }
        }
        
        async function testTranscriptProcessing() {
            const resultDiv = document.getElementById('processing-result');
            
            try {
                const response = await chrome.runtime.sendMessage({
                    type: 'PROCESS_TRANSCRIPT',
                    data: {
                        video_id: 'test123',
                        title: 'Test Video',
                        channel_name: 'Test Channel',
                        duration: 300,
                        transcript: 'This is a test transcript for authentication testing.',
                        source: 'test'
                    }
                });
                
                if (response.success) {
                    resultDiv.innerHTML = `<span class="success">✅ Processing successful: ${response.data.job_id}</span>`;
                } else {
                    resultDiv.innerHTML = `<span class="error">❌ Processing failed: ${response.error}</span>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<span class="error">Error: ${error.message}</span>`;
            }
        }
        
        async function testLogout() {
            const resultDiv = document.getElementById('logout-result');
            
            try {
                const response = await chrome.runtime.sendMessage({
                    type: 'USER_LOGOUT'
                });
                
                if (response.success) {
                    resultDiv.innerHTML = `<span class="success">✅ Logout successful</span>`;
                    checkAuthStatus();
                } else {
                    resultDiv.innerHTML = `<span class="error">❌ Logout failed: ${response.error}</span>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<span class="error">Error: ${error.message}</span>`;
            }
        }
        
        // Initialize
        checkAuthStatus();
    </script>
</body>
</html>
```

---

## 🚀 Implementation Checklist

### Phase 1: Core Authentication (Week 1)
- [ ] Create authentication UI components (LoginModal, SignupModal, AuthGuard)
- [ ] Update background script with authentication handlers
- [ ] Update app store for authentication state management
- [ ] Update popup component to integrate authentication
- [ ] Test authentication flow in extension

### Phase 2: Backend Integration (Week 2)
- [ ] Update YouTube routes to require authentication
- [ ] Add weekly video limit database functions
- [ ] Update ingestion service for automatic email delivery
- [ ] Add quota checking and enforcement
- [ ] Test authenticated API requests

### Phase 3: Payment Integration (Week 3)
- [ ] Create Paddle routes and webhook handlers
- [ ] Add upgrade prompt components
- [ ] Implement checkout flow
- [ ] Add subscription management
- [ ] Test complete payment flow

### Phase 4: Testing & Deployment (Week 4)
- [ ] Run comprehensive test suite
- [ ] Test edge cases and error scenarios
- [ ] Update documentation
- [ ] Deploy to production
- [ ] Monitor and fix any issues

---

## 🎯 Success Criteria

- ✅ Users can sign up/login from extension
- ✅ Transcript extraction remains free for all users
- ✅ Summary generation requires authentication
- ✅ Free users limited to 1 video/week
- ✅ Paid users get unlimited summaries
- ✅ User emails automatically used for summary delivery
- ✅ Upgrade flow works seamlessly through Paddle
- ✅ No disruption to existing functionality
- ✅ All existing users maintain current access levels

---

## 📝 Notes for Implementation

1. **Backward Compatibility**: All existing functionality must continue to work
2. **Security**: Ensure JWT tokens are handled securely in the extension
3. **Error Handling**: Provide clear error messages for authentication failures
4. **User Experience**: Make the authentication flow as smooth as possible
5. **Testing**: Thoroughly test all edge cases before deployment
6. **Monitoring**: Set up logging to monitor authentication and payment events

This implementation guide provides the complete roadmap for adding authentication and payment functionality while preserving all existing features and ensuring a smooth user experience. 