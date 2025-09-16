from tools.registry import list_all_tools

def return_tools():
    tools = list_all_tools()
        
    # Log toools
    if tools:
        lines = []
        for tool in tools:
            name = getattr(tool, "name", "<unknown>")
            description = getattr(tool, "description", "").strip()
            # Keep description concise in logs
            if len(description) > 120:
                description = description[:117] + "..."
            lines.append(f"- {name}: {description}")
        return f"Loaded following tools (count={len(tools)}):\n{'\n'.join(lines)}"
    else:
        return "No tools loaded."