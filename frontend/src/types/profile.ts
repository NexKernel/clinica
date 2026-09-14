export interface ProfileUpdatePayload {
  full_name: string
  email: string
  username: string
}

export interface PasswordChangePayload {
  current_password: string
  new_password: string
}
