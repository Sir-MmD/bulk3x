# 🗄️ Bulk3X

Add Expiry and Traffic in Bulk to 3x-ui Databases

## ✨ Features

- **Bulk Expiry Extension**: Add days to hundreds of users at once.
- **Bulk Traffic Top-up**: Add GBs of bandwidth to user quotas.
- **Smart Filtering**: Automatically ignores disabled, unlimited, or expired accounts.
- **Safe & Sync**: Updates both the SQL tables and JSON configurations simultaneously for full panel compatibility.
- **Pretty UI**: Built with [Rich](https://github.com/Textualize/rich) for a premium interactive experience.

## 🚀 Installation

1.  Clone the repository or download `bulk3x.py`.
2.  Install the requirement:
   
    ```bash
    pip install rich
    ```

## 🛠️ Usage

1.  Place `bulk3x.py`. in the same directory as your `.db` files.
2.  Run the script:

    ```bash
    python3 bulk3x.py
    ```
3.  Follow the interactive menu to select your database, inbound group, and operation.

## ⚠️ Integrity Check
This script modifies your database. It is highly recommended to **backup your `.db` files** before running bulk operations.
