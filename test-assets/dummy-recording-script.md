# Dummy Recording Script

Use this script to create a short test recording that matches the dummy transcript.

## Goal

Create a 2-4 minute walkthrough video with visible screen actions so the app can test:

- step extraction
- timestamp alignment
- derived screenshots
- transcript-based business rule extraction

## Suggested Setup

Use any screen recorder you already have, for example:

- Windows Game Bar
- OBS
- Teams recording on a demo screen share

Use these windows during the recording:

- Outlook or a mail client
- Excel
- Chrome or Edge
- any simple web form that can act as a finance portal

You do not need real business systems. A mock browser form and sample Excel file are enough.

## Recording Flow

Record yourself doing the following actions in order:

1. Open the AP inbox.
2. Open one invoice email.
3. Copy the invoice number from the subject.
4. Open an Excel tracker.
5. Paste the invoice number.
6. Copy the invoice amount from the email or attachment preview.
7. Paste the amount in Excel.
8. Mark a priority column as High.
9. Open a browser-based finance portal or any mock form.
10. Navigate to a create invoice screen.
11. Paste the invoice number into a reference field.
12. Enter vendor name.
13. Enter amount.
14. Click Submit.
15. Copy a generated reference number.
16. Return to Excel.
17. Paste the reference number.
18. Update status to Submitted.
19. Save the file.
20. Return to the email and type a reply note.

## Important Recording Tips

- Keep the cursor visible.
- Pause briefly after each step so frame extraction has cleaner moments.
- Make sure fields and buttons are visible before clicking.
- Avoid switching too fast between windows.
- Keep the recording resolution readable.

## Matching Transcript

Use this transcript with the recording:

- [dummy-transcript.txt](C:\Users\work\Documents\PddGenerator\test-assets\dummy-transcript.txt)

## Recommended First Test

For the first run, use:

- this transcript
- a short screen recording following the above steps
- a simple DOCX template

This will give the app a much better chance of producing meaningful steps and screenshots than using a random recording.
