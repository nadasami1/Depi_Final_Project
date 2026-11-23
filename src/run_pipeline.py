"""Run local preparation, quality checks, Gold model and trend outputs."""
from build_warehouse import build
from make_trends import main as make_trends
from build_powerbi import main as build_powerbi

if __name__ == "__main__":
    build()
    make_trends()
    build_powerbi()
