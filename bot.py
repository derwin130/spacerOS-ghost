import os
import random
import discord

from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

from database import (
    setup_database,
    create_operation,
    get_operation_by_code,
    get_active_operations,
    join_operation,
    mark_ready,
    get_participants,
    add_dispatch,
    close_operation,
)

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing from .env")


intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


def generate_op_code():
    return f"SC-{random.randint(100, 999)}"


def build_operation_embed(operation):
    operation_id = operation[0]
    op_code = operation[1]
    name = operation[2]
    op_type = operation[3]
    location = operation[4]
    risk = operation[5]
    status = operation[6]
    departure_time = operation[7]
    created_by = operation[8]

    participants = get_participants(operation_id)

    if participants:
        crew_lines = []
        ready_count = 0

        for person in participants:
            discord_name, role, ready = person

            if ready:
                ready_count += 1
                ready_status = "READY"
            else:
                ready_status = "PENDING"

            crew_lines.append(
                f"`{ready_status}` {discord_name} — {role}"
            )

        crew_text = "\n".join(crew_lines)
        readiness = f"{ready_count}/{len(participants)} ready"

    else:
        crew_text = "No crew assigned."
        readiness = "0/0 ready"

    embed = discord.Embed(
        title=f"GHOST // OPERATION {op_code}",
        description=f"**{name}**",
        color=discord.Color.dark_gold()
    )

    embed.add_field(name="Type", value=op_type, inline=True)
    embed.add_field(name="Location", value=location, inline=True)
    embed.add_field(name="Risk", value=risk, inline=True)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Departure", value=departure_time, inline=True)
    embed.add_field(name="Readiness", value=readiness, inline=True)
    embed.add_field(name="Crew Manifest", value=crew_text, inline=False)

    embed.set_footer(
        text=f"Created by {created_by} | SpacerOS Operations Terminal"
    )

    return embed


@bot.event
async def on_ready():
    setup_database()

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as error:
        print(error)

    print(f"GHOST online as {bot.user}")


@bot.tree.command(
    name="op-create",
    description="Create a new operation."
)
@app_commands.describe(
    name="Operation name",
    op_type="Cargo Escort, Mining, Security, etc.",
    location="Operation location",
    risk="Low, Medium, High, Critical",
    departure_time="When the operation begins"
)
async def op_create(
    interaction: discord.Interaction,
    name: str,
    op_type: str,
    location: str,
    risk: str,
    departure_time: str
):
    op_code = generate_op_code()

    create_operation(
        op_code=op_code,
        name=name,
        op_type=op_type,
        location=location,
        risk=risk.upper(),
        departure_time=departure_time,
        created_by=interaction.user.display_name
    )

    operation = get_operation_by_code(op_code)

    embed = build_operation_embed(operation)

    await interaction.response.send_message(
        content=(
            f"GHOST uplink established.\n\n"
            f"Operation `{op_code}` registered.\n"
            f"Crew assignment is now open."
        ),
        embed=embed
    )


@bot.tree.command(
    name="op-list",
    description="List active operations."
)
async def op_list(interaction: discord.Interaction):
    operations = get_active_operations()

    if not operations:
        await interaction.response.send_message(
            "No active operations found."
        )
        return

    lines = []

    for op in operations:
        lines.append(
            f"`{op[1]}` — {op[2]} | {op[3]} | {op[4]} | Risk: {op[5]}"
        )

    embed = discord.Embed(
        title="GHOST // ACTIVE OPERATIONS",
        description="\n".join(lines),
        color=discord.Color.dark_gold()
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="op-status",
    description="View operation details."
)
async def op_status(
    interaction: discord.Interaction,
    op_code: str
):
    operation = get_operation_by_code(op_code)

    if not operation:
        await interaction.response.send_message(
            f"Operation `{op_code}` not found.",
            ephemeral=True
        )
        return

    embed = build_operation_embed(operation)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="op-join",
    description="Join an operation."
)
async def op_join(
    interaction: discord.Interaction,
    op_code: str,
    role: str
):
    operation = get_operation_by_code(op_code)

    if not operation:
        await interaction.response.send_message(
            f"Operation `{op_code}` not found.",
            ephemeral=True
        )
        return

    operation_id = operation[0]

    join_operation(
        operation_id,
        str(interaction.user.id),
        interaction.user.display_name,
        role.upper()
    )

    operation = get_operation_by_code(op_code)

    embed = build_operation_embed(operation)

    await interaction.response.send_message(
        content=(
            f"GHOST assignment confirmed.\n\n"
            f"{interaction.user.mention} assigned as `{role.upper()}`."
        ),
        embed=embed
    )


@bot.tree.command(
    name="op-ready",
    description="Mark yourself ready."
)
async def op_ready(
    interaction: discord.Interaction,
    op_code: str
):
    operation = get_operation_by_code(op_code)

    if not operation:
        await interaction.response.send_message(
            f"Operation `{op_code}` not found.",
            ephemeral=True
        )
        return

    success = mark_ready(
        operation[0],
        str(interaction.user.id)
    )

    if not success:
        await interaction.response.send_message(
            "You are not assigned to this operation.",
            ephemeral=True
        )
        return

    operation = get_operation_by_code(op_code)

    embed = build_operation_embed(operation)

    await interaction.response.send_message(
        content="Readiness confirmed.",
        embed=embed
    )


@bot.tree.command(
    name="dispatch",
    description="Post a dispatch update."
)
async def dispatch(
    interaction: discord.Interaction,
    op_code: str,
    message: str
):
    operation = get_operation_by_code(op_code)

    if not operation:
        await interaction.response.send_message(
            f"Operation `{op_code}` not found.",
            ephemeral=True
        )
        return

    add_dispatch(
        operation[0],
        message,
        interaction.user.display_name
    )

    embed = discord.Embed(
        title=f"GHOST DISPATCH // {op_code.upper()}",
        description=message,
        color=discord.Color.red()
    )

    embed.set_footer(
        text=f"Filed by {interaction.user.display_name}"
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="op-close",
    description="Close an operation."
)
async def op_close(
    interaction: discord.Interaction,
    op_code: str
):
    operation = get_operation_by_code(op_code)

    if not operation:
        await interaction.response.send_message(
            f"Operation `{op_code}` not found.",
            ephemeral=True
        )
        return

    close_operation(operation[0])

    await interaction.response.send_message(
        f"Operation `{op_code.upper()}` archived.\n\n"
        f"GHOST session terminated."
    )


bot.run(TOKEN)
