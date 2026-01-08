#!/usr/bin/env python3
"""
Main entry point for the Polymarket Signal MCP Server.
This server exposes Polymarket data as read-only signals via FastMCP.
"""
import asyncio
from src.signal_server.mcp_server import mcp_server
from src.signal_server.config import settings


def main():
    """Main entry point for the signal server."""
    print("=" * 60)
    print("Polymarket Signal Server (FastMCP)")
    print("=" * 60)
    print(f"Region: {settings.USER_REGION}")
    print(f"Polymarket Execution Allowed: {settings.ALLOW_POLYMARKET_EXECUTION}")
    print(f"US Execution Allowed: {settings.ALLOW_US_EXECUTION}")
    print(f"Risk-Free Rate: {settings.RISK_FREE_RATE * 100:.2f}%")
    print("=" * 60)
    print()

    if settings.ALLOW_POLYMARKET_EXECUTION:
        print("WARNING: ALLOW_POLYMARKET_EXECUTION is set to True.")
        print("This server is READ-ONLY by design. No execution should occur on Polymarket.")
        print("Please set ALLOW_POLYMARKET_EXECUTION=false in your .env file.")
        print()

    print("Starting FastMCP server...")
    print("The server will expose the following:")
    print("  - Resource: polymarket://probability/{condition_id}")
    print("  - Tool: get_arb_spread(event_id, regulated_price, days_to_expiry)")
    print()
    print("Press Ctrl+C to stop the server.")
    print()

    try:
        # Run the MCP server
        # FastMCP typically uses mcp_server.run() which starts the server
        # For stdio mode (CLI), this will read from stdin and write to stdout
        mcp_server.run()
    except KeyboardInterrupt:
        print("\n\nShutting down signal server...")
    except Exception as e:
        print(f"\n\nError running signal server: {e}")
        raise


if __name__ == "__main__":
    main()
