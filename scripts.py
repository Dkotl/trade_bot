import subprocess
import sys

# Словарь с вашими короткими командами (аналог "scripts" в package.json)
SCRIPTS = {
    "download": "docker compose run --rm freqtrade download-data --pairs BTC/USDT:USDT ETH/USDT:USDT SOL/USDT:USDT BNB/USDT:USDT ADA/USDT:USDT AAVE/USDT:USDT AVAX/USDT:USDT APE/USDT:USDT --timeframes 4h --days 300 --trading-mode futures",
    "test": "docker compose run --rm freqtrade backtesting --config user_data/config.json --strategy BollingerRsiScalper --pairs BTC/USDT:USDT ETH/USDT:USDT SOL/USDT:USDT BNB/USDT:USDT ADA/USDT:USDT AAVE/USDT:USDT AVAX/USDT:USDT APE/USDT:USDT",
    "start": "docker compose up -d",
    "stop": "docker compose down",
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in SCRIPTS:
        print(f"Допустимые команды: {list(SCRIPTS.keys())}")
        sys.exit(1)

    cmd = SCRIPTS[sys.argv[1]]
    # Запуск bash-команды через Python
    subprocess.run(cmd, shell=True)


if __name__ == "__main__":
    main()
