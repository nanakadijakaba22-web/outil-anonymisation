import asyncio
async def main():
    print("Async Start")
    await asyncio.sleep(1)
    print("Async End")
if __name__ == "__main__":
    asyncio.run(main())
