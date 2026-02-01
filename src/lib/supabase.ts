import { createClient, SupabaseClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://iofndonrjbuubyjlgilt.supabase.co'
const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlvZm5kb25yamJ1dWJ5amxnaWx0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk4NjQ4OTYsImV4cCI6MjA4NTQ0MDg5Nn0._q9oE9ge2C1EDK5LTky4ySPvZHyQTqT243VddtbBEik'

// Create client only on client-side
let supabaseInstance: SupabaseClient | null = null

export const getSupabase = () => {
  if (typeof window === 'undefined') {
    // Return a dummy for SSR - won't be used
    return null
  }
  
  if (!supabaseInstance) {
    supabaseInstance = createClient(supabaseUrl, supabaseAnonKey)
  }
  
  return supabaseInstance
}

// For backward compatibility
export const supabase = typeof window !== 'undefined' 
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null as unknown as SupabaseClient

// Types for our data
export interface Ping {
  id: string
  lat: number
  lng: number
  created_at: string
  type?: string
  label?: string
  severity?: string
  confidence?: number
  // Additional fields for ticket display
  street_name?: string
  image_url?: string
  effort_minutes?: number
  status?: string
}
