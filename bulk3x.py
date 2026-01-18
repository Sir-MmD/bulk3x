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

# Initialize Console
console = Console()

def print_header():
    console.print(Panel.fit(
        "[bold cyan]Bulk3X[/bold cyan]\n[dim]Add Expiry and Traffic in Bulk to 3x-ui Databases[/dim]",
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
    
    table.add_row("", "")
    table.add_row("[red]0[/red]", "[red]Exit[/red]")

    console.print(table)
    
    while True:
        choice = IntPrompt.ask("Enter choice number", default=0)
        if choice == 0:
            console.print("[yellow]Exiting...[/yellow]")
            sys.exit(0)
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
    console.print("[dim]Enter [bold red]0[/bold red] to go Back to DB selection[/dim]")

    while True:
        choice = IntPrompt.ask("Enter choice number")
        if choice == 0:
            return 'BACK'
        if choice == 1:
            return 'ALL'
        if choice - 1 in inbound_map:
            return inbound_map[choice - 1]
        console.print("[red]Invalid choice. Please try again.[/red]")

def menu_select_op():
    table = Table(title="Select Operation", box=box.ROUNDED, show_header=False)
    table.add_column("No.", style="cyan", justify="right")
    table.add_column("Operation", style="bold white")
    
    table.add_row("1", "Add Days to Expiry")
    table.add_row("2", "Add Traffic (GB)")
    
    console.print(table)
    console.print("[dim]Enter [bold red]0[/bold red] to go Back[/dim]")

    while True:
        choice = IntPrompt.ask("Enter choice number")
        if choice == 0:
            return 'BACK'
        if choice in [1, 2]:
            return choice - 1
        console.print("[red]Invalid choice.[/red]")

def main():
    while True:
        console.clear()
        print_header()
        
        # 1. Select Database
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

            while True: # Inbound Loop
                # 2. Select Inbound
                inbounds = get_inbounds(cursor)
                selected_inbound_id = menu_select_inbound(inbounds)
                
                if selected_inbound_id == 'BACK':
                    conn.close()
                    break 

                target_desc = "[bold]ALL users[/bold]" if selected_inbound_id == 'ALL' else f"Users in Inbound ID ( [bold cyan]{selected_inbound_id}[/bold cyan] )"
                
                while True: # Operation Loop
                    console.print(Panel(f"Targeting: {target_desc}", style="blue"))

                    # 3. Select Operation
                    op_idx = menu_select_op()
                    if op_idx == 'BACK':
                        break
                    
                    current_time_ms = int(time.time() * 1000)

                    if op_idx == 0: # Expiry
                        days = IntPrompt.ask("Enter number of [bold]DAYS[/bold] to add (Enter 0 to cancel)")
                        if days <= 0: continue
                        
                        ms_to_add = days * 24 * 60 * 60 * 1000
                        
                        # PRE-FLIGHT CHECK
                        console.print("\n[yellow]Scanning candidates...[/yellow]")
                        
                        if selected_inbound_id == 'ALL':
                            cursor.execute("SELECT id, settings FROM inbounds")
                        else:
                            cursor.execute("SELECT id, settings FROM inbounds WHERE id = ?", (selected_inbound_id,))
                        
                        rows = cursor.fetchall()
                        updates_count = 0
                        eligible_clients = [] # List of (inbound_id, settings_dict, client_obj, client_email)

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
                                        is_enabled = client.get('enable', False)
                                        if isinstance(is_enabled, str): is_enabled = is_enabled.lower() in ('true', '1')
                                        elif isinstance(is_enabled, int): is_enabled = is_enabled == 1
                                            
                                        expiry = client.get('expiryTime', 0)
                                        
                                        # ENABLED + LIMITED + NOT EXPIRED
                                        if is_enabled and expiry > 0 and expiry > current_time_ms:
                                            eligible_clients.append({
                                                'inbound_id': inbound_id,
                                                'settings': settings, # Note: this is a reference to the dict we parsed earlier? 
                                                # Careful: multiple clients in same inbound share 'settings' dict.
                                                # We need to group by inbound to save efficiently.
                                                'client': client
                                            })
                                            updates_count += 1
                                except: pass
                        
                        if updates_count == 0:
                            console.print("[bold red]No matching users found.[/bold red] (Conditions: Enabled, Time-Limited, Not Expired)")
                            continue

                        # Confirmation Panel
                        console.print(Panel(
                            f"[bold]Operation:[/bold] Add [cyan]{days}[/cyan] Days\n"
                            f"[bold]Target:[/bold] {target_desc}\n"
                            f"[bold]Eligible Users:[/bold] [green]{updates_count}[/green]",
                            title="Confirm Update",
                            border_style="yellow"
                        ))
                        
                        if not Confirm.ask("Proceed with update?"):
                            console.print("[yellow]Cancelled.[/yellow]")
                            continue

                        # EXECUTE UPDATE
                        # Group by inbound to minimize JSON dumps
                        inbound_updates = {} # id -> settings
                        updated_emails = []
                        
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
                                client['expiryTime'] = client.get('expiryTime', 0) + ms_to_add
                                
                                i_id = item['inbound_id']
                                if i_id not in inbound_updates:
                                    inbound_updates[i_id] = item['settings']
                                
                                email = client.get('email')
                                if email: updated_emails.append(email)
                                
                                progress.advance(update_task)

                            # Save to DB
                            save_task = progress.add_task("Saving to Database...", total=len(inbound_updates))
                            for i_id, settings in inbound_updates.items():
                                new_settings = json.dumps(settings)
                                cursor.execute("UPDATE inbounds SET settings = ? WHERE id = ?", (new_settings, i_id))
                                progress.advance(save_task)
                            
                            # Update Client Traffics Table
                            if updated_emails:
                                sync_task = progress.add_task("Syncing client_traffics...", total=len(updated_emails))
                                chunk_size = 900
                                for i in range(0, len(updated_emails), chunk_size):
                                    chunk = updated_emails[i:i+chunk_size]
                                    placeholders = ','.join('?' for _ in chunk)
                                    sql = f"UPDATE client_traffics SET expiry_time = expiry_time + ? WHERE email IN ({placeholders})"
                                    params = [ms_to_add] + chunk
                                    cursor.execute(sql, params)
                                    progress.advance(sync_task, advance=len(chunk))
                        
                        conn.commit()
                        console.print(f"\n[bold green]✔ Successfully updated {updates_count} users.[/bold green]")


                    elif op_idx == 1: # Traffic
                        gb = FloatPrompt.ask("Enter amount of Traffic in [bold]GB[/bold] to add (Enter 0 to cancel)")
                        if gb <= 0: continue
                        
                        bytes_to_add = int(gb * 1024 * 1024 * 1024)
                        
                        console.print("\n[yellow]Scanning candidates...[/yellow]")
                        
                        if selected_inbound_id == 'ALL':
                            cursor.execute("SELECT id, settings FROM inbounds")
                        else:
                            cursor.execute("SELECT id, settings FROM inbounds WHERE id = ?", (selected_inbound_id,))
                        
                        rows = cursor.fetchall()
                        updates_count = 0
                        eligible_clients = []

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
                                        is_enabled = client.get('enable', False)
                                        if isinstance(is_enabled, str): is_enabled = is_enabled.lower() in ('true', '1')
                                        elif isinstance(is_enabled, int): is_enabled = is_enabled == 1
                                            
                                        total = client.get('totalGB', 0)
                                        expiry = client.get('expiryTime', 0)
                                        
                                        # Check if expired
                                        is_not_expired = True
                                        if expiry > 0 and expiry < current_time_ms:
                                            is_not_expired = False
                                        
                                        # ENABLED + LIMITED TRAFFIC + NOT EXPIRED
                                        if is_enabled and total > 0 and is_not_expired:
                                            eligible_clients.append({
                                                'inbound_id': inbound_id,
                                                'settings': settings,
                                                'client': client
                                            })
                                            updates_count += 1
                                except: pass
                        
                        if updates_count == 0:
                            console.print("[bold red]No matching users found.[/bold red] (Conditions: Enabled, Traffic-Limited, Not Expired)")
                            continue

                        console.print(Panel(
                            f"[bold]Operation:[/bold] Add [cyan]{gb}[/cyan] GB\n"
                            f"[bold]Target:[/bold] {target_desc}\n"
                            f"[bold]Eligible Users:[/bold] [green]{updates_count}[/green]",
                            title="Confirm Update",
                            border_style="yellow"
                        ))
                        
                        if not Confirm.ask("Proceed with update?"):
                            console.print("[yellow]Cancelled.[/yellow]")
                            continue

                        inbound_updates = {}
                        updated_emails = []
                        
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
                                client['totalGB'] = client.get('totalGB', 0) + bytes_to_add
                                
                                i_id = item['inbound_id']
                                if i_id not in inbound_updates:
                                    inbound_updates[i_id] = item['settings']
                                
                                email = client.get('email')
                                if email: updated_emails.append(email)
                                progress.advance(update_task)

                            save_task = progress.add_task("Saving to Database...", total=len(inbound_updates))
                            for i_id, settings in inbound_updates.items():
                                new_settings = json.dumps(settings)
                                cursor.execute("UPDATE inbounds SET settings = ? WHERE id = ?", (new_settings, i_id))
                                progress.advance(save_task)
                            
                            if updated_emails:
                                sync_task = progress.add_task("Syncing client_traffics...", total=len(updated_emails))
                                chunk_size = 900
                                for i in range(0, len(updated_emails), chunk_size):
                                    chunk = updated_emails[i:i+chunk_size]
                                    placeholders = ','.join('?' for _ in chunk)
                                    sql = f"UPDATE client_traffics SET total = total + ? WHERE email IN ({placeholders})"
                                    params = [bytes_to_add] + chunk
                                    cursor.execute(sql, params)
                                    progress.advance(sync_task, advance=len(chunk))

                        conn.commit()
                        console.print(f"\n[bold green]✔ Successfully updated {updates_count} users.[/bold green]")

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
