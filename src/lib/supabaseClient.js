import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://iofndonrjbuubyjlgilt.supabase.co'
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlvZm5kb25yamJ1dWJ5amxnaWx0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk4NjQ4OTYsImV4cCI6MjA4NTQ0MDg5Nn0._q9oE9ge2C1EDK5LTky4ySPvZHyQTqT243VddtbBEik'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

