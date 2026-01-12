import httpx
import asyncio
import json
import sys
import time

API_URL = "http://localhost:4096"
HEADERS = {"Content-Type": "application/json"}


async def get_active_session():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{API_URL}/session")
            if resp.status_code != 200:
                print(f"❌ Failed to list sessions: {resp.status_code}")
                return None

            sessions = resp.json()
            if not sessions:
                print("❌ No active sessions found.")
                return None

            # Sort by updated time desc to get the one we've been using
            # The API returns them in a list, we can just grab the first one or search
            # We want the one that is NOT the current ab_test runner if possible,
            # but usually 'opencode serve' manages the sessions.
            # We'll just pick the first one which is likely our active sub-agent.
            session_id = sessions[0]["id"]
            print(f"✅ Found active session: {session_id}")
            return session_id
        except Exception as e:
            print(f"❌ Error connecting to API: {e}")
            return None


async def send_prompt(session_id, text):
    async with httpx.AsyncClient() as client:
        url = f"{API_URL}/session/{session_id}/prompt_async"
        payload = {"parts": [{"type": "text", "text": text}]}
        try:
            resp = await client.post(url, json=payload, headers=HEADERS)
            if resp.status_code in (200, 204):
                print(f"✅ Successfully injected prompt: '{text}'")
                return True
            else:
                print(f"❌ Failed to inject prompt: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"❌ Error sending prompt: {e}")
            return False


async def verify_response(session_id, unique_id, timeout=30):
    print(f"⏳ Polling session logs for {timeout} seconds to verify execution...")
    start_time = time.time()

    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                # Get recent messages
                resp = await client.get(f"{API_URL}/session/{session_id}/message")
                if resp.status_code == 200:
                    data = resp.json()  # Parse as JSON to inspect structure

                    # We need to find a tool call that contains our unique_id in the input
                    for msg in data:
                        if "parts" in msg:
                            for part in msg["parts"]:
                                if (
                                    part.get("type") == "tool"
                                    and part.get("tool") == "bash"
                                ):
                                    command = (
                                        part.get("state", {})
                                        .get("input", {})
                                        .get("command", "")
                                    )
                                    if (
                                        unique_id in command
                                        and "send_telegram.py" in command
                                    ):
                                        print(
                                            f"✅ Verified: Found specific tool call for ID {unique_id}"
                                        )
                                        return True
            except Exception as e:
                # print(f"Polling error: {e}")
                pass

            await asyncio.sleep(2)

    print("❌ Verification timed out. Sub-agent did not appear to execute the command.")
    return False


async def main():
    print("🚀 Starting A/B Test for Opencode API Integration")

    session_id = await get_active_session()
    if not session_id:
        sys.exit(1)

    # Generate a unique ID for this test run
    test_id = f"TEST_RUN_{int(time.time())}"
    prompt_text = (
        f"A/B TEST {test_id}: If you receive this, please immediately run "
        f'`./venv/bin/python send_telegram.py "A/B Test {test_id} Successful."`'
    )

    if await send_prompt(session_id, prompt_text):
        success = await verify_response(session_id, test_id)
        if success:
            print(
                "\n🎉 TEST PASSED: The API bridge is functioning correctly without human intervention."
            )
        else:
            print(
                "\nQw TEST FAILED: The API accepted the prompt, but the sub-agent didn't execute the tool."
            )
            sys.exit(1)
    else:
        print("\nQw TEST FAILED: Could not inject prompt via API.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
