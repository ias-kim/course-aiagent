import os
import threading
import asyncio

async def main():
    print(f"Process ID: {os.getpid()}")
    print(f"Thread name: {threading.current_thread().name}")
    print(f"Thread name: {threading.get_ident()}")
    print(f"20초 대기")
    await asyncio.sleep(20)


if __name__ == "__main__":
    asyncio.run(main())
