 Bright Studio — AI Appointment Booking Assistant

A RAG chat + calendar  based booking system for a skincare/beauty studio. Customers can browse
services, ask questions, and book real appointments. Staff can manage bookings and even set up
their business (hours, services) by chatting with an AI assistant.

---

 Part 1: Problem Understanding:
 
Many small businesses, like skincare clinics or beauty studios, spend a lot of time answering phone calls and messages just to book appointments. Customers usually don't know which time slots are available, so they have to wait for a reply or keep asking until they find a free time.

Our system makes this process simple. Customers can visit the website, see the available services, check real-time open slots on the calendar, and book an appointment instantly without calling or messaging anyone. They can also ask the AI assistant questions about business hours, service prices, reviews, or booking policies. After choosing a time, they just enter their name and email, and they receive a booking confirmation with an **"Add to Calendar"** button. Customers can also sign in using only their name to view their upcoming appointments or cancel them if needed.

For the business staff or admin, there is a secure login to manage all appointments. They can view bookings, mark them as completed or cancelled, and update business details easily. Instead of filling out long forms, they simply tell the setup assistant something like, **"We're open from 9 AM to 6 PM, Monday to Saturday,"** and the system updates the business hours immediately. Customers will instantly see the new timings while booking appointments.


---

 Part 2: Spec & Plan

1. System design (high level)

```
                     ┌─────────────────────┐
                     │   React Frontend     │
                     │ (booking calendar,   │
                     │  chat widget, admin) │
                     └──────────┬───────────┘
                                │ REST API (JSON)
                     ┌──────────▼───────────┐
                     │   FastAPI Backend     │
                     │  (Python)             │
                     └──────────┬───────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                        │
┌───────▼────────┐   ┌──────────▼─────────┐   ┌──────────▼─────────┐
│  Postgres DB     │   │  AI Agent (Grok)    │   │  RAG Knowledge Base │
│  (appointments,   │   │  via LangChain,     │   │  (FAISS vector      │
│  services,        │   │  answers questions  │   │  search over policy │
│  customers,        │   │  using tools        │   │  documents)          │
│  business settings)│   └─────────────────────┘   └─────────────────────┘
└────────────────────┘
```

In plain words: the website (frontend) talks to a Python server (backend). The server keeps all
the real data (bookings, services, business hours) in a database. When a customer or staff
member chats with the AI, the server sends the conversation to Grok (the AI model), gives it a
list of "tools" it's allowed to use (like "check what times are free"), and the AI decides which
tool to use. The AI **never directly changes the database itself** — it can only ask the tool to
do it, and the tool is plain, tested Python code. This keeps bookings safe and correct even if
the AI makes a mistake in wording.

 2. Feature breakdown

Customer side
- Sign in with just a name (optional email) — no password needed
- Browse services with price and duration
- Pick a date and time on a calendar — slots that are already booked are greyed out and can't be
  clicked
- Book an appointment instantly, get a ticket-style confirmation
- Download the appointment as a calendar file (.ics) to add to Google/Apple Calendar
- See their own upcoming appointments and cancel them
- Chat with "Aria" (the AI) to ask about services, hours, reviews, or policies — the chat cannot
  book for you on purpose, it just helps you decide, then you book on the calendar
Staff side
- Log in with a username and password
- Dashboard: today's bookings, charts of bookings by day/service, list of all appointments
- Mark appointments as completed, cancelled, or no-show
- **Setup Assistant**: a chat where staff type things like "we're open 8 to 6" or "add service
  Facial Peel, 30 min, $45" and the business updates immediately
- A manual settings form as a backup, in case staff prefer clicking instead of typing

Behind the scenes**
- Real double-booking prevention (checked in the database, not just in the AI's head)
- Business hours are stored in the database and can change live, without restarting anything
- If the AI (Grok) isn't connected, the whole app still works using simple rule-based logic
  instead — so nothing breaks if there's no API key

3. Prompt design

The AI is given a short instruction ("system prompt") before every conversation, telling it:
- What today's date is, and what the business hours are
- What tools it's allowed to use (see below)
- Rules like: "never say a booking succeeded unless the tool says so", "ask for missing
  information one thing at a time", "if asked to book, tell the customer to use the calendar
  instead"

We use two separate AI agents with two separate prompts and tool sets:
1. Customer assistant** — can only look things up (services, hours, reviews, availability). It
   cannot create or cancel bookings, on purpose — booking happens on the calendar, not through
   chat.
2. **Staff setup assistant** — can change business hours, business info, and services. Locked
   behind a password since it can affect what every customer sees.

4. Data model (simplified)

| Table | What it stores |
|---|---|
| `services` | Name, duration, price, description |
| `customers` | Name, email, phone |
| `appointments` | Which customer, which service, start/end time, status (confirmed/cancelled/completed/no-show) |
| `business_settings` | Business name, hours, open days, address, phone |
| `reviews` | Customer name, rating, comment |
| `admin_users` | Staff login (username + hashed password) |
| `chat_sessions` / `chat_messages` | Conversation history for the AI chat |

 5. Implementation plan

1. Build the booking rules first (business hours, no double-booking) as plain Python — test it
   thoroughly before adding any AI.
2. Build the database and basic REST API (list services, book, cancel, reschedule).
3. Add the AI chat layer on top, using tools that call the same booking code from step 1.
4. Add the knowledge base (RAG) so the AI can answer policy questions correctly instead of
   guessing.
5. Build the frontend: calendar booking UI, chat widget, name-only login.
6. Build the staff dashboard, setup assistant, and manual settings form.
7. Test everything, write this documentation, record the demo.

---

Part 3: Implementation

Tech stack

- Backend**: Python, FastAPI (web server), SQLAlchemy (database access), PostgreSQL
  (database), Alembic (database migrations)
- **AI**: [LangChain](https://www.langchain.com) (framework for connecting AI models to tools),
  **Grok** (xAI's AI model) as the language model, FAISS (a vector search library) for the
  knowledge base search
- **Frontend**: React + TypeScript, Vite (build tool), Tailwind CSS (styling), Recharts (charts
  on the dashboard)

 Which AI model, and why

We used **Grok (xAI)** as the main conversational model, connected through LangChain.

- LangChain was chosen because it gives a ready-made, well-tested way to let an AI model call
  "tools" (functions) safely, and it makes it easy to swap AI providers later without rewriting
  everything.
- Grok specifically was chosen per the assignment/task requirement. It's connected through
  LangChain's standard interface, so if needed later, swapping to a different model (like GPT or
  Claude) would only need a small config change, not a rewrite.
- We also built a **fallback mode**: if there's no Grok API key set, the app automatically
  switches to simple, rule-based Python logic (pattern matching, not AI) so the whole system
  still works for demo/testing purposes without needing a paid API key.

 How this was built

This project was built using help of **Claude** (Anthropic's AI coding assistant) inside a chat
interface, working step by step: debugging the  backend code, testing it immediately after each
change, fixing real bugs that testing found (for example, a booking-conflict edge case and a
database connection bug), then building the matching frontend, and finally packaging everything
into a ready-to-run project.

Because this was built interactively over many turns rather than in one single API call, there
isn't one "total token count" the way there would be for a single automated script — Claude was
used conversationally throughout the whole build, the same way a developer would use it as a
coding assistant, not as a one-shot code generator.

 Project structure

```
appointment-ai/
├── backend/
│   ├── app/
│   │   ├── models/          (database tables)
│   │   ├── routers/         (API endpoints)
│   │   ├── services/        (booking rules, AI agents, RAG)
│   │   ├── schemas/         (data validation)
│   │   └── knowledge_base/  (policy documents the AI can search)
│   └── tests/                (automated tests — 43 tests, all passing)
├── frontend/
│   └── src/
│       ├── components/       (chat widget, calendar, ticket cards, etc.)
│       ├── pages/            (landing page, admin dashboard, admin login)
│       └── lib/               (API calls, formatting helpers)
└── docker-compose.yml         (runs the whole thing with one command)
```

---

 Part 4: Edge Cases

These are the tricky situations we specifically thought about and tested:

1. Two people try to book the same time slot at once** — the second request is rejected with
   a clear "that slot was just taken" message, and the calendar refreshes to show the real
   availability. This check happens in the database, not in the AI, so it's always correct.
2. Booking in the past** — rejected with a clear message.
3. Booking outside business hours or on a closed day** — rejected; and since hours are stored
   in the database (not hardcoded), this stays correct even after staff change the hours.
4 .Booking too far in the future** — capped at 30 days ahead.
5. Cancelling and then rebooking the same slot** — allowed, since a cancelled slot becomes free
   again.
6. Rescheduling into a slot that's already taken by someone else** — rejected.
7. Rescheduling into the exact same time it already had** — allowed (doesn't falsely think it
   conflicts with itself).
8. No AI API key configured** — the whole app still works using simple rule-based logic
   instead of breaking.
9. The AI is asked to book something — it politely declines and points the customer to the
   calendar, since booking is intentionally kept out of the AI's hands to avoid mistakes.
10. A customer asks a policy question mid-conversation** — the AI answers from the actual
    policy documents (RAG search) instead of guessing.
11. A customer types a service name that's just one word, like "massage" instead of the full
    "Deep Tissue Massage"** — the system still matches it correctly.
12. A customer isn't signed in but tries to cancel an appointment** — cancelling only works
    through their own "My Appointments" list, tied to their email.
13. Timezones** — all times are stored in one consistent format internally and converted
    correctly for display, so bookings don't shift by a few hours by mistake.

---

How to run it

See the separate step-by-step setup guide (PDF) provided earlier, or the quick version:

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL, and optionally XAI_API_KEY
python -m app.seed
python -m app.build_rag_index
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
```

Then open `http://localhost:5173`.
