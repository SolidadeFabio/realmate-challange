import os
import sys
import time
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'realmate_challenge.settings')
django.setup()

from webhooks.tasks import (
    create_single_conversation,
    create_conversation_batch,
    simulate_peak_hour,
    simulate_conversation_flow
)
from webhooks.services import ConversationService
from webhooks.models import Conversation, Message
from celery import group
import uuid


def populate_with_batches():
    print("=" * 60)
    print("ASYNC DATABASE POPULATION - BATCH MODE")
    print("=" * 60)

    num_batches = 10
    conversations_per_batch = 100
    total_conversations = num_batches * conversations_per_batch

    print(f"Creating {total_conversations} conversations in {num_batches} batches")
    print(f"Each batch: {conversations_per_batch} conversations")
    print("=" * 60)

    start_time = datetime.now() - timedelta(hours=8)

    for i in range(num_batches):
        batch_time = start_time + timedelta(minutes=i*10)
        result = create_conversation_batch.delay(
            num_conversations=conversations_per_batch,
            start_time=batch_time.isoformat()
        )
        print(f"Batch {i+1}/{num_batches} dispatched - Task ID: {result.id}")
        time.sleep(2)

    print("\nAll batches dispatched!")
    print("Monitor progress at http://localhost:5555 (Flower dashboard)")


def populate_with_concurrent_tasks():
    """
    Populate database by spawning many individual conversation tasks.
    This creates a more realistic simulation with individual conversations.
    """
    print("=" * 60)
    print("ASYNC DATABASE POPULATION - CONCURRENT TASKS")
    print("=" * 60)

    num_conversations = 500
    print(f"Creating {num_conversations} conversations concurrently")
    print("=" * 60)

    base_time = datetime.now() - timedelta(hours=4)
    tasks = []

    for i in range(num_conversations):
        random_offset = i % 240
        timestamp = base_time + timedelta(minutes=random_offset)

        task = create_single_conversation.si(timestamp.isoformat())
        tasks.append(task)

    print(f"Dispatching {len(tasks)} conversation tasks...")
    job = group(tasks)
    result = job.apply_async()

    print(f"Group task dispatched - ID: {result.id}")
    print("\nTasks are being processed asynchronously!")
    print("Monitor progress at http://localhost:5555 (Flower dashboard)")


def simulate_realistic_peak():
    """
    Simulate a realistic peak hour scenario.
    This creates conversations over time to simulate real traffic patterns.
    """
    print("=" * 60)
    print("ASYNC DATABASE POPULATION - PEAK HOUR SIMULATION")
    print("=" * 60)

    duration = 30
    conversations_per_minute = 20

    print(f"Simulating {duration} minutes of peak traffic")
    print(f"Average: {conversations_per_minute} conversations per minute")
    print(f"Expected total: ~{duration * conversations_per_minute} conversations")
    print("=" * 60)

    result = simulate_peak_hour.delay(
        duration_minutes=duration,
        conversations_per_minute=conversations_per_minute
    )

    print(f"Peak hour simulation started - Task ID: {result.id}")
    print("This will run for the specified duration")
    print("Monitor progress at http://localhost:5555 (Flower dashboard)")


def create_live_conversations():
    """
    Create conversations that simulate live ongoing chats.
    Messages are added progressively to simulate real-time conversation.
    """
    print("=" * 60)
    print("ASYNC DATABASE POPULATION - LIVE CONVERSATIONS")
    print("=" * 60)

    num_live_conversations = 50
    print(f"Creating {num_live_conversations} live conversations")
    print("Messages will be added progressively to simulate real chat")
    print("=" * 60)

    conversation_service = ConversationService()
    base_time = datetime.now()

    conversation_ids = []

    for i in range(num_live_conversations):
        conversation_id = str(uuid.uuid4())
        conversation_service.create_conversation(conversation_id, base_time)
        conversation_ids.append(conversation_id)

    print(f"Created {len(conversation_ids)} conversations")
    print("Now spawning tasks to simulate message flow...")

    tasks = []
    for conv_id in conversation_ids:
        num_messages = 5 + (conversation_ids.index(conv_id) % 10)
        task = simulate_conversation_flow.si(conv_id, num_messages=num_messages)
        tasks.append(task)

    job = group(tasks)
    result = job.apply_async()

    print(f"Message flow simulation started - Group ID: {result.id}")
    print("Messages will be added with realistic delays")
    print("Monitor progress at http://localhost:5555 (Flower dashboard)")


def show_statistics():
    """
    Show current database statistics.
    """
    print("\n" + "=" * 60)
    print("DATABASE STATISTICS")
    print("=" * 60)

    total_conversations = Conversation.objects.count()
    open_conversations = Conversation.objects.filter(status='OPEN').count()
    closed_conversations = Conversation.objects.filter(status='CLOSED').count()
    total_messages = Message.objects.count()

    avg_messages = 0
    if total_conversations > 0:
        avg_messages = total_messages / total_conversations

    print(f"Total conversations: {total_conversations}")
    print(f"  - Open: {open_conversations}")
    print(f"  - Closed: {closed_conversations}")
    print(f"Total messages: {total_messages}")
    print(f"Average messages per conversation: {avg_messages:.1f}")
    print("=" * 60)


def main():
    """
    Main function to run the population script.
    """
    print("\n🚀 CELERY-BASED DATABASE POPULATION SCRIPT")
    print("=" * 60)
    print("Choose population method:")
    print("1. Batch creation (fastest)")
    print("2. Concurrent individual tasks")
    print("3. Peak hour simulation (realistic)")
    print("4. Live conversations (with progressive messages)")
    print("5. Run all methods")
    print("6. Show statistics only")
    print("=" * 60)

    try:
        choice = input("Enter your choice (1-6): ").strip()

        if choice == '1':
            populate_with_batches()
        elif choice == '2':
            populate_with_concurrent_tasks()
        elif choice == '3':
            simulate_realistic_peak()
        elif choice == '4':
            create_live_conversations()
        elif choice == '5':
            print("\n🔥 Running all population methods...\n")
            populate_with_batches()
            time.sleep(5)
            populate_with_concurrent_tasks()
            time.sleep(5)
            create_live_conversations()
            time.sleep(5)
            simulate_realistic_peak()
        elif choice == '6':
            pass
        else:
            print("Invalid choice. Showing statistics only.")

        time.sleep(3)
        show_statistics()

        print("\n✅ Population script completed!")
        print("📊 Check Flower dashboard for task monitoring: http://localhost:5555")
        print("🔍 Test the API: http://localhost/conversations/{conversation_id}/")

    except KeyboardInterrupt:
        print("\n\n⚠️ Population interrupted by user.")
        show_statistics()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()