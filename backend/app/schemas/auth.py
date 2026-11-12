from pydantic import BaseModel, model_validator, Field, EmailStr
from typing import Optional

class OTPRequest(BaseModel):
    phone: Optional[str] = Field(None, description="10-digit mobile number")
    email: Optional[str] = Field(None, description="Email address")
    purpose: Optional[str] = Field("auth", description="'auth', 'registration', 'password_reset'")

    @model_validator(mode="after")
    def check_identifier(self):
        if not self.phone and not self.email:
            raise ValueError("Either phone or email must be provided")
        return self

class OTPRequestResponse(BaseModel):
    status: str
    message: str
    masked_target: str
    cooldown_seconds: int = 60
    demo_otp: Optional[str] = Field(None, description="Simulated OTP provided for hackathon/local testing")

class OTPVerify(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    otp: str = Field(..., min_length=4, max_length=6, description="OTP code")

    @model_validator(mode="after")
    def check_identifier(self):
        if not self.phone and not self.email:
            raise ValueError("Either phone or email must be provided to verify OTP")
        return self

class SessionResponse(BaseModel):
    session_token: str
    access_token: Optional[str] = None
    user_id: str
    full_name: Optional[str] = None
    role: str = "citizen"
    expires_at: str
    consent_required: bool
    masked_identifier: str

class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Applicant full legal name")
    email: str = Field(..., description="Email address")
    phone: str = Field(..., min_length=10, max_length=15, description="10-digit mobile number")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    confirm_password: str = Field(..., description="Confirm password")

class UserRegisterVerifyRequest(BaseModel):
    identifier: str = Field(..., description="Email or mobile number")
    otp: str = Field(..., min_length=4, max_length=6, description="6-digit verification code")

class UserLoginRequest(BaseModel):
    identifier: str = Field(..., description="Email or 10-digit mobile number")
    password: str = Field(..., min_length=1, description="Account password")

class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(..., description="Registered email or mobile number")

class ResetPasswordRequest(BaseModel):
    identifier: str = Field(..., description="Registered email or mobile number")
    otp: str = Field(..., min_length=4, max_length=6, description="6-digit verification code")
    new_password: str = Field(..., min_length=6, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")

class DemoLoginRequest(BaseModel):
    role: str = Field("student", description="'student' or 'admin'")

class UserProfileResponse(BaseModel):
    id: str
    full_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    role: str
    created_at: Optional[str]
    has_consent: bool
