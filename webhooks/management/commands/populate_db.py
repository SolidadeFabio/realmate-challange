from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from celery import group

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from webhooks.tasks import (
    create_single_conversation,
    create_conversation_batch,
    simulate_peak_hour
)
from webhooks.models import Conversation, Message


console = Console()


class Command(BaseCommand):
    help = 'Populate database with conversations and messages using Celery tasks'

    def handle(self, *args, **options):
        console.clear()

        console.print(Panel.fit(
            "[bold cyan]DATABASE POPULATION WITH CELERY[/bold cyan]\n"
            "[dim]Populate your database with realistic conversation data[/dim]",
            border_style="cyan",
            box=box.DOUBLE
        ))

        mode = self.get_mode()

        if mode == 'batch':
            self.populate_batch_mode()
        elif mode == 'concurrent':
            self.populate_concurrent_mode()
        elif mode == 'peak':
            self.populate_peak_mode()

        self.show_statistics()

    def get_mode(self):
        console.print("\n[bold yellow]Select population mode:[/bold yellow]")
        console.print("  [cyan]1.[/cyan] Batch mode - Create conversations in organized batches")
        console.print("  [cyan]2.[/cyan] Concurrent mode - Create all conversations simultaneously")
        console.print("  [cyan]3.[/cyan] Peak mode - Simulate peak hour traffic")

        choice = Prompt.ask(
            "\n[bold]Choose mode[/bold]",
            choices=["1", "2", "3"],
            default="1"
        )

        modes = {"1": "batch", "2": "concurrent", "3": "peak"}
        return modes[choice]

    def populate_batch_mode(self):
        console.print("\n[bold green]BATCH MODE[/bold green]")

        total = IntPrompt.ask(
            "[cyan]How many conversations to create?[/cyan]",
            default=100
        )

        batch_size = IntPrompt.ask(
            "[cyan]Conversations per batch?[/cyan]",
            default=50
        )

        num_batches = (total + batch_size - 1) // batch_size
        base_time = timezone.now() - timedelta(hours=4)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                f"[cyan]Dispatching {num_batches} batches...",
                total=num_batches
            )

            for i in range(num_batches):
                conversations_in_batch = min(batch_size, total - i * batch_size)
                batch_time = base_time + timedelta(minutes=i*10)

                result = create_conversation_batch.delay(
                    num_conversations=conversations_in_batch,
                    start_time=batch_time.isoformat()
                )

                progress.update(
                    task,
                    advance=1,
                    description=f"[green]✓[/green] Batch {i+1}/{num_batches} dispatched (Task: {result.id[:8]}...)"
                )

        console.print(f"\n[bold green]All {num_batches} batches dispatched successfully![/bold green]")

    def populate_concurrent_mode(self):
        console.print("\n[bold green]CONCURRENT MODE[/bold green]")

        num_conversations = IntPrompt.ask(
            "[cyan]How many conversations to create?[/cyan]",
            default=100
        )

        base_time = timezone.now() - timedelta(hours=2)
        tasks = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]Preparing tasks...",
                total=num_conversations
            )

            for i in range(num_conversations):
                offset_minutes = (i * 5) % 120
                timestamp = base_time + timedelta(minutes=offset_minutes)
                celery_task = create_single_conversation.si(timestamp.isoformat())
                tasks.append(celery_task)
                progress.update(task, advance=1)

        job = group(tasks)
        result = job.apply_async()

        console.print(f"\n[bold green]Dispatched {len(tasks)} concurrent tasks![/bold green]")
        console.print(f"[dim]Group ID: {result.id}[/dim]")

    def populate_peak_mode(self):
        console.print("\n[bold green]PEAK HOUR SIMULATION MODE[/bold green]")

        duration_minutes = IntPrompt.ask(
            "[cyan]Peak duration in minutes?[/cyan]",
            default=30
        )

        conversations_per_minute = IntPrompt.ask(
            "[cyan]Conversations per minute?[/cyan]",
            default=10
        )

        total = duration_minutes * conversations_per_minute

        confirm = Confirm.ask(
            f"\n[yellow]This will create ~{total} conversations. Continue?[/yellow]",
            default=True
        )

        if not confirm:
            console.print("[red]Operation cancelled[/red]")
            return

        with console.status("[bold cyan]Starting peak hour simulation...", spinner="dots"):
            result = simulate_peak_hour.delay(
                duration_minutes=duration_minutes,
                conversations_per_minute=conversations_per_minute
            )

        console.print(f"\n[bold green]Peak simulation started![/bold green]")
        console.print(f"[dim]Task ID: {result.id}[/dim]")
        console.print(f"[dim]Expected conversations: ~{total}[/dim]")

    def show_statistics(self):
        console.print("\n")

        stats = {
            'Total conversations': Conversation.objects.count(),
            'Open conversations': Conversation.objects.filter(status='OPEN').count(),
            'Closed conversations': Conversation.objects.filter(status='CLOSED').count(),
            'Total messages': Message.objects.count(),
        }

        table = Table(
            title="Current Database Statistics",
            box=box.ROUNDED,
            border_style="cyan"
        )

        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Count", style="magenta", justify="right")

        for key, value in stats.items():
            table.add_row(key, str(value))

        if stats['Total conversations'] > 0:
            avg_messages = stats['Total messages'] / stats['Total conversations']
            table.add_row(
                "Avg messages/conversation",
                f"{avg_messages:.1f}",
                style="bold yellow"
            )

        console.print(table)

        console.print(Panel(
            "[bold green]Tasks dispatched successfully![/bold green]\n"
            "[cyan]Monitor progress at:[/cyan] http://localhost:5555",
            border_style="green",
            box=box.ROUNDED
        ))
