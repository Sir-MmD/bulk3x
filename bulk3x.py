#!/usr/bin/env python3
import sqlite3
import glob
import sys
import time
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import box
from rich.text import Text

console = Console()

def ask_int(prompt_text, default=None):
    while True:
        val = Prompt.ask(prompt_text, default=str(default) if default is not None else None)
        if val and val.strip().lower() == 'x':
            console.print("[yellow]Exiting...[/yellow]")
            sys.exit(0)
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
        if val is None or val == "":
             continue
        console.print("[red]Please enter a valid integer (or 'x' to exit).[/red]")

def ask_float(prompt_text, default=None):
    while True:
        val = Prompt.ask(prompt_text, default=str(default) if default is not None else None)
        if val and val.strip().lower() == 'x':
            console.print("[yellow]Exiting...[/yellow]")
            sys.exit(0)
        try:
            return float(val)
        except (ValueError, TypeError):
            pass
        if val is None or val == "":
            continue
        console.print("[red]Please enter a valid number (or 'x' to exit).[/red]")

def get_client_stats(cursor):
    stats = {}
    try:
        temp_cursor = cursor.connection.cursor()
        temp_cursor.execute("SELECT email, up, down FROM client_traffics")
        for row in temp_cursor.fetchall():
            email = row['email']
            if email:
                stats[email.strip().lower()] = {'up': row['up'], 'down': row['down']}
        temp_cursor.close()
    except Exception as e:
        console.print(f"[bold red]Warning: Failed to fetch client stats:[/bold red] {e}")
    return stats

def is_user_active(client, stats):
    # 1. Check Explicit Enable
    is_enabled = client.get('enable', False)
    if isinstance(is_enabled, str): is_enabled = is_enabled.lower() in ('true', '1')
    elif isinstance(is_enabled, int): is_enabled = is_enabled == 1
    
    if not is_enabled: return False

    # 2. Check Expiry
    expiry = client.get('expiryTime', 0)
    current_time_ms = int(time.time() * 1000)
    if expiry > 0 and expiry < current_time_ms: return False
    
    # 3. Check Traffic
    total = client.get('totalGB', 0)
    if total > 0:
        email = client.get('email')
        if email:
            usage = stats.get(email.strip().lower(), {'up':0, 'down':0})
            used = usage['up'] + usage['down']
            if used >= total: return False
        
    return True


def print_header():
    console.print(Panel.fit(
        "[bold cyan]Bulk3X[/bold cyan]\n[dim]Manage Expiry and Traffic Quotas with Ease[/dim]",
        border_style="cyan",
        padding=(1, 2)
    ))

def get_db_files():
    files = glob.glob("*.db")
    files.sort()
    return files

def get_inbounds(cursor):
    try:
        cursor.execute("SELECT id, tag, protocol, port, remark, settings FROM inbounds")
        return cursor.fetchall()
    except sqlite3.Error as e:
        console.print(f"[bold red]Failed to fetch inbounds:[/bold red] {e}")
        return []

def menu_select_db(options):
    table = Table(title="Select Database", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("No.", style="cyan", width=4, justify="right")
    table.add_column("Database File", style="green")

    for i, opt in enumerate(options):
        table.add_row(str(i + 1), opt)
    
    console.print(table)
    console.print("[dim]Enter [bold red]x[/bold red] to Exit script[/dim]")
    
    while True:
        choice = ask_int("Enter choice number", default=1 if options else None) 
        
        if 1 <= choice <= len(options):
            return choice - 1
        console.print("[red]Invalid choice. Please try again.[/red]")

def menu_select_inbound(inbounds):
    table = Table(title="Select Inbound Scope", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("No.", style="cyan", width=4, justify="right")
    table.add_column("ID", style="dim")
    table.add_column("Tag", style="bold white")
    table.add_column("Details", style="yellow")
    table.add_column("Users", style="green") 

    # Option 1: All Inbounds
    table.add_row("1", "ALL", "[bold]ALL INBOUNDS[/bold]", "Apply to all users", "-")
    
    inbound_map = {0: 'ALL'}
    
    for i, row in enumerate(inbounds):
        # Quick stats parsing
        user_count = 0
        try:
            settings = json.loads(row['settings'])
            clients = settings.get('clients', [])
            if isinstance(clients, list):
                user_count = len(clients)
        except:
            user_count = "?"

        remark = row['remark'] if row['remark'] else ""
        details = f"{row['protocol']} ({row['port']}) {remark}"
        
        idx = i + 2
        table.add_row(str(idx), str(row['id']), row['tag'], details, str(user_count))
        inbound_map[idx - 1] = row['id']

    console.print(table)
    console.print("[dim]Enter [bold red]0[/bold red] to go Back, or [bold red]x[/bold red] to Exit script[/dim]")

    while True:
        choice = ask_int("Enter choice number")
        if choice == 0:
            return 'BACK'
        if choice == 1:
            return 'ALL'
        if choice - 1 in inbound_map:
            return inbound_map[choice - 1]
        console.print("[red]Invalid choice. Please try again.[/red]")

def menu_select_user_status():
    table = Table(title="Select User Status", box=box.ROUNDED, show_header=False)
    table.add_column("No.", style="cyan", justify="right")
    table.add_column("Status", style="bold white")
    
    table.add_row("1", "Active Users Only")
    table.add_row("2", "Disabled Users Only")
    table.add_row("3", "All Users (Active & Disabled)")
    
    console.print(table)
    console.print("[dim]Enter [bold red]0[/bold red] to go Back, or [bold red]x[/bold red] to Exit script[/dim]")

    while True:
        choice = ask_int("Enter choice number")
        if choice == 0:
            return 'BACK'
        if choice == 1:
            return 'ACTIVE'
        if choice == 2:
            return 'DISABLED'
        if choice == 3:
            return 'ALL'
        console.print("[red]Invalid choice.[/red]")

def main():
    while True:
        console.clear()
        print_header()
        
        db_files = get_db_files()
        if not db_files:
            console.print("[bold red]No .db files found in current directory.[/bold red]")
            return

        db_idx = menu_select_db(db_files)
        db_file = db_files[db_idx]
        
        try:
            conn = sqlite3.connect(db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            console.print(f"[green]✔ Connected to {db_file}[/green]")

            while True: 
                inbounds = get_inbounds(cursor)
                selected_inbound_id = menu_select_inbound(inbounds)
                
                if selected_inbound_id == 'BACK':
                    conn.close()
                    break 

                user_status = menu_select_user_status()
                if user_status == 'BACK':
                    continue

                target_desc = "[bold]ALL users[/bold]" if selected_inbound_id == 'ALL' else f"Users in Inbound ID ( [bold cyan]{selected_inbound_id}[/bold cyan] )"
                target_desc += f" [yellow][ {user_status} ][/yellow]"
                
                while True:
                    console.print(Panel(f"Targeting: {target_desc}", style="blue"))

                    days = ask_int("Enter number of [bold]DAYS[/bold] to add (Enter 0 to skip, x to exit)", default=0)
                    gb = ask_float("Enter amount of [bold]Traffic (GB)[/bold] to add (Enter 0 to skip, x to exit)", default=0.0)

                    if days <= 0 and gb <= 0.0:
                        console.print("[yellow]No changes requested. Returning to database selection...[/yellow]")
                        break 
                        
                    ms_to_add = days * 24 * 60 * 60 * 1000
                    bytes_to_add = int(gb * 1024 * 1024 * 1024)

                    console.print("\n[yellow]Scanning candidates...[/yellow]")
                    
                    if selected_inbound_id == 'ALL':
                        cursor.execute("SELECT id, settings FROM inbounds")
                    else:
                        cursor.execute("SELECT id, settings FROM inbounds WHERE id = ?", (selected_inbound_id,))
                    
                    rows = cursor.fetchall()
                    
                    eligible_clients = [] 
                    
                    client_stats = get_client_stats(cursor)

                    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
                        task = progress.add_task("Parsing Inbounds...", total=len(rows))
                        
                        for row in rows:
                            inbound_id = row['id']
                            settings_str = row['settings']
                            progress.advance(task)
                            if not settings_str: continue
                            
                            try:
                                settings = json.loads(settings_str)
                                clients = settings.get('clients', [])
                                if not isinstance(clients, list): continue
                                
                                for client in clients:
                                    # Skip Start-on-First-Use (negative expiry)
                                    if client.get('expiryTime', 0) < 0: continue
                                    
                                    # Check Status (Active/Disabled/All)
                                    is_active = is_user_active(client, client_stats)
                                    
                                    is_status_match = False
                                    if user_status == 'ALL': is_status_match = True
                                    elif user_status == 'ACTIVE': is_status_match = is_active
                                    elif user_status == 'DISABLED': is_status_match = not is_active
                                    
                                    if not is_status_match: continue

                                    # Determine necessary updates
                                    do_expiry = False
                                    do_traffic = False

                                    # Update Expiry if days requested (>0) and user has specific expiry (>0)
                                    expiry = client.get('expiryTime', 0)
                                    if days > 0 and expiry > 0:
                                        do_expiry = True

                                    # Update Traffic if GB requested (>0) and user has specific totalGB (>0)
                                    total_gb = client.get('totalGB', 0)
                                    if gb > 0 and total_gb > 0:
                                        do_traffic = True
                                        
                                    if do_expiry or do_traffic:
                                        eligible_clients.append({
                                            'inbound_id': inbound_id,
                                            'settings': settings,
                                            'client': client,
                                            'do_expiry': do_expiry,
                                            'do_traffic': do_traffic
                                        })

                            except: pass
                    
                    updates_count = len(eligible_clients)
                    if updates_count == 0:
                        console.print("[bold red]No matching users found for the requested criteria.[/bold red]")
                        break

                    op_summary = []
                    if days > 0: op_summary.append(f"Add [cyan]{days}[/cyan] Days")
                    if gb > 0: op_summary.append(f"Add [cyan]{gb}[/cyan] GB")
                    
                    console.print(Panel(
                        f"[bold]Operation:[/bold] {', '.join(op_summary)}\n"
                        f"[bold]Target:[/bold] {target_desc}\n"
                        f"[bold]Eligible Users:[/bold] [green]{updates_count}[/green]",
                        title="Confirm Update",
                        border_style="yellow"
                    ))
                    
                    if not Confirm.ask("Proceed with update?"):
                        console.print("[yellow]Cancelled.[/yellow]")
                        break

                    inbound_updates = {}
                    emails_expiry_update = []
                    emails_traffic_update = []
                    
                    with Progress(
                        SpinnerColumn(), 
                        BarColumn(), 
                        TaskProgressColumn(), 
                        TextColumn("[progress.description]{task.description}"), 
                        transient=False
                    ) as progress:
                        update_task = progress.add_task("Applying Updates...", total=updates_count)
                        
                        for item in eligible_clients:
                            client = item['client']
                            
                            if item['do_expiry']:
                                client['expiryTime'] = client.get('expiryTime', 0) + ms_to_add
                                if client.get('email'): emails_expiry_update.append(client['email'])

                            if item['do_traffic']:
                                client['totalGB'] = client.get('totalGB', 0) + bytes_to_add
                                if client.get('email'): emails_traffic_update.append(client['email'])
                            
                            i_id = item['inbound_id']
                            if i_id not in inbound_updates:
                                inbound_updates[i_id] = item['settings']
                            
                            progress.advance(update_task)

                        save_task = progress.add_task("Saving to Database...", total=len(inbound_updates))
                        for i_id, settings in inbound_updates.items():
                            new_settings = json.dumps(settings)
                            cursor.execute("UPDATE inbounds SET settings = ? WHERE id = ?", (new_settings, i_id))
                            progress.advance(save_task)
                        
                        if emails_expiry_update:
                            sync_exp_task = progress.add_task("Syncing Expiry...", total=len(emails_expiry_update))
                            chunk_size = 900
                            for i in range(0, len(emails_expiry_update), chunk_size):
                                chunk = emails_expiry_update[i:i+chunk_size]
                                placeholders = ','.join('?' for _ in chunk)
                                sql = f"UPDATE client_traffics SET expiry_time = expiry_time + ? WHERE email IN ({placeholders})"
                                params = [ms_to_add] + chunk
                                cursor.execute(sql, params)
                                progress.advance(sync_exp_task, advance=len(chunk))

                        if emails_traffic_update:
                            sync_trf_task = progress.add_task("Syncing Traffic...", total=len(emails_traffic_update))
                            chunk_size = 900
                            for i in range(0, len(emails_traffic_update), chunk_size):
                                chunk = emails_traffic_update[i:i+chunk_size]
                                placeholders = ','.join('?' for _ in chunk)
                                sql = f"UPDATE client_traffics SET total = total + ? WHERE email IN ({placeholders})"
                                params = [bytes_to_add] + chunk
                                cursor.execute(sql, params)
                                progress.advance(sync_trf_task, advance=len(chunk))

                    conn.commit()
                    console.print(f"\n[bold green]✔ Successfully updated {updates_count} users.[/bold green]")
                    console.print("[dim]Enter [bold red]0[/bold red] to go Back, or [bold red]x[/bold red] to Exit script[/dim]")
                    ask_int("Enter choice number", default=0)
                    
                    break

        except sqlite3.Error as e:
            console.print(f"[bold red]Database error:[/bold red] {e}")
            if conn: conn.close()
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]An error occurred:[/bold red] {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
