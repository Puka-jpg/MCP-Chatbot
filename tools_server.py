import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tools_neuralflow")

@mcp.tool()
def save_contact_info(name: str, phone: str, email: str) -> str:
    """Save complete contact information (Claude handles all parsing)"""
    try:
        os.makedirs("./neuralflow_docs/user_info", exist_ok=True)
        
        entry = f"""
=== CONTACT REQUEST ===
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Name: {name}
Phone: {phone}
Email: {email}
========================

"""
        with open("./neuralflow_docs/user_info/contacts.txt", "a") as f:
            f.write(entry)
        
        return f"✅ Thanks {name}! We'll contact you soon at {phone} or {email}."
        
    except Exception as e:
        return f"❌ Error saving contact information: {str(e)}"

@mcp.tool()
def save_appointment(name: str, date: str, phone: str = "", email: str = "") -> str:
    """Save complete appointment information (Claude handles all parsing)"""
    try:
        os.makedirs("./neuralflow_docs/user_info", exist_ok=True)
        
        entry = f"""
=== APPOINTMENT REQUEST ===
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Appointment Date: {date}
Name: {name}
Phone: {phone}
Email: {email}
Status: confirmed
===========================

"""
        with open("./neuralflow_docs/user_info/appointments.txt", "a") as f:
            f.write(entry)
        
        contact_info = ""
        if phone and email:
            contact_info = f" We'll confirm the exact time with you at {phone} or {email}."
        elif phone:
            contact_info = f" We'll confirm the exact time with you at {phone}."
        elif email:
            contact_info = f" We'll confirm the exact time with you at {email}."
        
        return f"✅ Appointment booked successfully!\n\n📅 {name} - {date}\n💾 Your appointment has been saved.{contact_info}"
        
    except Exception as e:
        return f"❌ Error saving appointment: {str(e)}"

if __name__ == "__main__":
    print("Starting NeuralFlow Simple Tools Server...")
    mcp.run(transport='stdio')