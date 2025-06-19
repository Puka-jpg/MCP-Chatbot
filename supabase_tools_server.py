import os
from mcp.server.fastmcp import FastMCP
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
mcp = FastMCP("tools_neuralflow")

# Connect to database
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@mcp.tool()
def save_contact_info(name: str, phone: str, email: str) -> str:
    """Save user contact information"""
    try:
        # Clean up the data
        clean_phone = ''.join(filter(str.isdigit, phone)) if phone else ""
        
        # Check if user already exists
        existing = supabase.table("users").select("*").eq("email", email.lower()).execute()
        
        if existing.data:
            return f"Thanks {name}! We already have your contact information."
        
        # Save new user
        user_data = {
            "name": name.strip(),
            "email": email.lower().strip(),
            "phone": clean_phone
        }
        
        supabase.table("users").insert(user_data).execute()
        return f"Thanks {name}! We'll contact you soon at {email}."
        
    except Exception as e:
        return "Sorry, there was a technical issue. Please try again."

@mcp.tool()
def save_appointment(name: str, date: str, phone: str = "", email: str = "") -> str:
    """Save appointment booking"""
    try:
        clean_phone = ''.join(filter(str.isdigit, phone)) if phone else ""
        
        # Find or create user
        existing_user = supabase.table("users").select("*").eq("email", email.lower()).execute()
        
        if existing_user.data:
            user_id = existing_user.data[0]["id"]
        else:
            # Create new user
            user_data = {
                "name": name.strip(),
                "email": email.lower().strip(),
                "phone": clean_phone
            }
            new_user = supabase.table("users").insert(user_data).execute()
            user_id = new_user.data[0]["id"]
        
        # Save appointment
        appointment_data = {
            "user_id": user_id,
            "appointment_date": date.strip(),
            "status": "requested"
        }
        
        supabase.table("appointments").insert(appointment_data).execute()
        return f"Appointment booked successfully!\n\n{name} - {date}\n Your appointment has been saved."
        
    except Exception as e:
        return "Sorry, there was a technical issue saving your appointment. Please try again."

@mcp.tool()
def update_appointment_status(user_email: str, appointment_date: str, new_status: str) -> str:
    """Update appointment status"""
    try:
        # Find user
        user_result = supabase.table("users").select("id").eq("email", user_email.lower()).execute()
        user_id = user_result.data[0]["id"]
        
        # Update appointment
        supabase.table("appointments")\
            .update({"status": new_status})\
            .eq("user_id", user_id)\
            .eq("appointment_date", appointment_date)\
            .execute()
        
        return f"Appointment status updated to '{new_status}'"
        
    except Exception as e:
        return f"Error updating appointment status"

if __name__ == "__main__":
    print("Starting NeuralFlow Tools Server...")
    mcp.run(transport='stdio')