from pathlib import Path

log_file = Path("data/io_test.log")

def main():
    print(f"Attempting to write to {log_file}...")
    try:
        log_file.parent.mkdir(exist_ok=True)
        with log_file.open("w") as f:
            f.write("File I/O Verification Test: SUCCESS\n")
        print("File write successful.")
    except Exception as e:
        print(f"File write FAILED: {e}")

if __name__ == "__main__":
    main()
