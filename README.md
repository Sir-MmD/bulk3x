# 🗄️ Bulk3X

Add Expiry and Traffic in Bulk to 3x-ui Databases

![App Screenshot](https://raw.githubusercontent.com/Sir-MmD/bulk3x/refs/heads/main/screenshot.png)
![App Screenshot](https://raw.githubusercontent.com/Sir-MmD/bulk3x/refs/heads/main/screenshot1.png)
![App Screenshot](https://raw.githubusercontent.com/Sir-MmD/bulk3x/refs/heads/main/screenshot2.png)

## ✨ Features

- **Smart Filtering**: Target **Active Users**, **Disabled Users**, or **All Users**.
- **Unified Operations**: Add **Days** and **Traffic (GB)** in a single pass.
- **Safety First**:
    - Automatic handling of "Start on First Use" accounts (never modified/initialized accidentally).
    - Respects **Unlimited** Duration/Traffic accounts (skips them appropriately).
    - Checks actual `client_traffics` to determine if a user is truly disabled (expired or out of traffic).
- **Safe & Sync**: Updates both specific SQL tables and embedded JSON configurations simultaneously.
- **Pretty UI**: Built with [Rich](https://github.com/Textualize/rich) for a premium interactive experience.

## 🚀 Installation

1.  Clone the repository or download `bulk3x.py`.
2.  Install the requirement:
   
    ```bash
    pip install rich
    ```

## 🛠️ Usage

1.  Place `bulk3x.py` in the same directory as your `.db` files.
2.  Run the script:
   
    ```bash
    python3 bulk3x.py
    ```
4.  **Select Database**: Choose the SQLite file to work on.
5.  **Select Inbound**: Pick a specific Inbound ID or apply to ALL.
6.  **Select Status**: Filter for Active, Disabled, or All users.
7.  **Apply Changes**: Enter the amount of Days and/or GB to add.
    - Enter `0` to skip adding either days or traffic.
    - Enter `x` to exit.

## ⚠️ Integrity Check
This script modifies your database. It is highly recommended to **backup your `.db` files** before running bulk operations.
