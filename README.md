# Donna
Be honest, is checking your phone the first thing you do after waking up? Well, you're not alone. Nearly 90% of people check their phones within 10 minutes of waking up. This overload of information can affect your cognitive ability and abruptly push your brain into a stressful cluttered state.

That's why at I built Donna - a personal AI Voice Agent that can keep you on track without the mindless scrolling. She can:
- Access your Calendar and Gmail
- Call you for reminders, unread emails, etc.
- Schedule new calendar events, reply to emails or even draft new ones
- Have realistic conversations in your preferred language

Built with **FastAPI**, **LangGraph**, **Twilio**, **Livekit** and **Groq**.

## Demo Guide

Follow these steps to run the demo locally and test Donna (Windows / PowerShell):

1. Clone the repository

	- Open PowerShell and run:

	```powershell
	git clone https://github.com/SwayamMehta10/donna.ai.git
	cd donna.ai
	```

2. Create a virtual environment

	```powershell
	python -m venv myENV
	# Activate the virtual environment in PowerShell
	.\myENV\Scripts\Activate.ps1
	```

3. Install dependencies

	```powershell
	pip install -r requirements.txt
	```

4. Start all servers

	- Use the included script to start all services. From the repo root run:

	```powershell
	.\start_all_servers.ps1
	```

5. Sign up using Google and enter your phone number

	- Open a browser and go to the web UI (default): `http://localhost:8000`
	- Use the Google sign-in flow to register / sign in.
	- After signing in, add your phone number in your profile.

6. Click the "Call me now" button

	- From the web UI click the `Call me now` button to trigger an outbound call.

7. IMPORTANT: Context Feature server prompt

	- In the **Context Feature** server terminal you will be prompted: `Do you want to make a reservation?`.
	- Enter `no` and press Enter.
	- This feature is incomplete and if you answer anything else the server may time out or block the call flow.

8. Accept the incoming call and talk to Donna

	- Wait for the phone call and accept it.
	- Try out different commands and features:
	  - Ask Donna to check your emails: say "How many emails do I have?" then say "Read out my emails" when prompted.
	  - Reply to an email: say "Reply to the email from John" after Donna reads out the first few emails (she will further ask you for the body)
	  - Draft a new email: say "Draft a new email" and follow Donna's prompts (she will ask for recipient, subject and body).
	  - Create calendar events: say "Create a new calendar event" and answer Donna's follow-up questions (title and start time).
	  - Ask to view your calendar: say "What's on my calendar?"

Notes and troubleshooting

- If you hit LLM rate limits or the agent becomes unresponsive, consider upgrading the Groq account tier (see `https://console.groq.com/settings/limits`) or change the model in `src/agents/agent.py` (the `llm` model parameter).
- If Donna interrupts you mid-sentence, the silence detector (VAD) threshold can be adjusted in `src/agents/agent.py` in `prewarm_process` (the `silero.VAD.load(min_silence_duration=...)` value).
- Email fetching may take a few seconds when retrieving many messages from Gmail; be patient after requesting emails.
- If a tool call fails with a validation error (e.g., `view_calendar`), the agent code includes safe fallbacks in `src/agents/functions.py`.

Enjoy testing Donna — if anything behaves unexpectedly, send the latest log and transcript files from the `logs/` and `temp/` folders and I can help debug.


