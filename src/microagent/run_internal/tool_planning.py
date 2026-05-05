"""Tool planning helpers.

Planning lives in `turn_resolution.process_model_response`. Approval-policy evaluation
(`needs_approval` bool vs. callable), MCP list-tools deduplication and tool-search
deferred-loading negotiation are handled by addons that subclass that pipeline.
"""