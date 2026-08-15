import asyncio

from dotenv import load_dotenv

from src.outbound import trigger_outbound_sip_call

load_dotenv(".env.local")


async def test():
    res = await trigger_outbound_sip_call("sip:cheese-cheese@sip.linphone.org", "Rahul")
    print("TEST SIP CALL RESULT:", res)


if __name__ == "__main__":
    asyncio.run(test())
