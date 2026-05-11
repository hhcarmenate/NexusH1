from integrations.notifications import check_gmail, check_notion, check_calendar

with open("test_notifications_output.txt", "w", encoding="utf-8") as f:
    f.write("=== GMAIL ===\n")
    result = check_gmail()
    f.write(result[:1000] if result else "No emails\n")
    
    f.write("\n=== NOTION ===\n")
    result = check_notion()
    f.write(result[:1000] if result else "No tasks\n")
    
    f.write("\n=== CALENDAR ===\n")
    result = check_calendar()
    f.write(result[:1000] if result else "No events\n")

print("Output saved to test_notifications_output.txt")