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
    leave_operation,
    mark_ready,
    get_participants,
    add_dispatch,
    close_operation,
    set_dispatch_channel,
    get_dispatch_channel,
)

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing from .env")

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)


def guild_id_from(interaction: discord.Interaction):
    return str(interaction.guild.id)


def generate_op_code():
    return f"SC-{random.randint(100, 999)}"


def risk_color(risk: str):
    risk = risk.upper()

    if risk == "LOW":
        return discord.Color.green()
    if risk == "MEDIUM":
        return discord.Color.gold()
    if risk == "HIGH":
        return discord.Color.orange()
    if risk == "CRITICAL":
        return discord.Color.red()

    return discord.Color.dark_gold()


def build_operation_embed(operation):
    operation_id = operation[0]
    op_code = operation[2]
    name = operation[3]
    op_type = operation[4]
    location = operation[5]
    risk = operation[6]
    status = operation[7]
    departure_time = operation[8]
    created_by = operation[9]

    participants = get_participants(operation_id)

    if participants:
        crew_lines = []
        ready_count = 0

        for discord_name, role, ready in participants:
            if ready:
                ready_count += 1
                ready_status = "READY"
            else:
                ready_status = "PENDING"

            crew_lines.append(f"`{ready_status}` {discord_name} — {role}")

        crew_text = "\n".join(crew_lines)
        readiness = f"{ready_count}/{len(participants)} ready"
    else:
        crew_text = "No crew assigned."
        readiness = "0/0 ready"

    embed = discord.Embed(
        title=f"GHOST // OPERATION {op_code}",
        description=f"**{name}**",
        color=risk_color(risk)
    )

    embed.add_field(name="Type", value=op_type, inline=True)
    embed.add_field(name="Location", value=location, inline=True)
    embed.add_field(name="Risk", value=risk, inline=True)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Departure", value=departure_time, inline=True)
    embed.add_field(name="Readiness", value=readiness, inline=True)
    embed.add_field(name="Crew Manifest", value=crew_text, inline=False)

    embed.set_footer(text=f"Created by {created_by} | SpacerOS Operations Terminal")

    return embed


@bot.event
async def on_ready():
    setup_database()

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as error:
        print(f"Slash command sync failed: {error}")

    print(f"GHOST online as {bot.user}")


@bot.tree.command(name="setup-dispatch", description="Set the channel where GHOST dispatch updates should be posted.")
@app_commands.describe(channel="The channel to use as the dispatch feed")
async def setup_dispatch(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = guild_id_from(interaction)

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "GHOST authorization failed. You need Manage Server permission to configure dispatch routing.",
            ephemeral=True
        )
        return

    set_dispatch_channel(guild_id, str(channel.id))

    await interaction.response.send_message(
        f"GHOST dispatch relay configured.\n\nDispatch updates will post to {channel.mention}."
    )


@bot.tree.command(name="op-create", description="Create a new operation.")
@app_commands.describe(
    name="Operation name",
    op_type="Cargo Escort, Mining, Security, Patrol, Salvage, etc.",
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
    guild_id = guild_id_from(interaction)
    op_code = generate_op_code()

    create_operation(
        guild_id=guild_id,
        op_code=op_code,
        name=name,
        op_type=op_type,
        location=location,
        risk=risk.upper(),
        departure_time=departure_time,
        created_by=interaction.user.display_name
    )

    operation = get_operation_by_code(guild_id, op_code)
    embed = build_operation_embed(operation)

    await interaction.response.send_message(
        content=(
            f"GHOST uplink established.\n\n"
            f"Operation `{op_code}` registered under SpacerOS.\n"
            f"Crew assignment is now open."
        ),
        embed=embed
    )


@bot.tree.command(name="op-list", description="List active operations for this server.")
async def op_list(interaction: discord.Interaction):
    guild_id = guild_id_from(interaction)
    operations = get_active_operations(guild_id)

    if not operations:
        await interaction.response.send_message(
            "GHOST scan complete. No active operations currently registered."
        )
        return

    lines = []

    for op in operations:
        op_code = op[2]
        name = op[3]
        op_type = op[4]
        location = op[5]
        risk = op[6]
        status = op[7]

        lines.append(
            f"`{op_code}` — **{name}** | {op_type} | {location} | Risk: {risk} | Status: {status}"
        )

    embed = discord.Embed(
        title="GHOST // ACTIVE OPERATIONS",
        description="\n".join(lines),
        color=discord.Color.dark_gold()
    )

    embed.set_footer(text="SpacerOS Operations Terminal")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="op-status", description="View operation details.")
@app_commands.describe(op_code="Example: SC-428")
async def op_status(interaction: discord.Interaction, op_code: str):
    guild_id = guild_id_from(interaction)
    operation = get_operation_by_code(guild_id, op_code)

    if not operation:
        await interaction.response.send_message(
            f"GHOST lookup failed. No active operation found under `{op_code.upper()}`.",
            ephemeral=True
        )
        return

    embed = build_operation_embed(operation)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="op-join", description="Join an operation.")
@app_commands.describe(
    op_code="Example: SC-428",
    role="Command, Cargo, Escort, Scout, Medical, Engineer, Security, Support"
)
async def op_join(interaction: discord.Interaction, op_code: str, role: str):
    guild_id = guild_id_from(interaction)
    operation = get_operation_by_code(guild_id, op_code)

    if not operation:
        await interaction.response.send_message(
            f"GHOST lookup failed. No active operation found under `{op_code.upper()}`.",
            ephemeral=True
        )
        return

    operation_id = operation[0]

    join_operation(
        operation_id=operation_id,
        discord_id=str(interaction.user.id),
        discord_name=interaction.user.display_name,
        role=role.upper()
    )

    updated_operation = get_operation_by_code(guild_id, op_code)
    embed = build_operation_embed(updated_operation)

    await interaction.response.send_message(
        content=(
            f"GHOST assignment confirmed.\n\n"
            f"{interaction.user.mention} assigned to `{op_code.upper()}` as `{role.upper()}`."
        ),
        embed=embed
    )


@bot.tree.command(name="op-leave", description="Leave an operation.")
@app_commands.describe(op_code="Example: SC-428")
async def op_leave(interaction: discord.Interaction, op_code: str):
    guild_id = guild_id_from(interaction)
    operation = get_operation_by_code(guild_id, op_code)

    if not operation:
        await interaction.response.send_message(
            f"GHOST lookup failed. No active operation found under `{op_code.upper()}`.",
            ephemeral=True
        )
        return

    success = leave_operation(
        operation_id=operation[0],
        discord_id=str(interaction.user.id)
    )

    if not success:
        await interaction.response.send_message(
            f"You are not currently assigned to `{op_code.upper()}`.",
            ephemeral=True
        )
        return

    updated_operation = get_operation_by_code(guild_id, op_code)
    embed = build_operation_embed(updated_operation)

    await interaction.response.send_message(
        content=f"{interaction.user.mention} removed from `{op_code.upper()}`.",
        embed=embed
    )


@bot.tree.command(name="op-ready", description="Mark yourself ready for an operation.")
@app_commands.describe(op_code="Example: SC-428")
async def op_ready(interaction: discord.Interaction, op_code: str):
    guild_id = guild_id_from(interaction)
    operation = get_operation_by_code(guild_id, op_code)

    if not operation:
        await interaction.response.send_message(
            f"GHOST lookup failed. No active operation found under `{op_code.upper()}`.",
            ephemeral=True
        )
        return

    success = mark_ready(
        operation_id=operation[0],
        discord_id=str(interaction.user.id)
    )

    if not success:
        await interaction.response.send_message(
            f"You are not assigned to `{op_code.upper()}`. Join first with `/op-join`.",
            ephemeral=True
        )
        return

    updated_operation = get_operation_by_code(guild_id, op_code)
    embed = build_operation_embed(updated_operation)

    await interaction.response.send_message(
        content=(
            f"Readiness confirmed.\n\n"
            f"{interaction.user.mention} is ready for `{op_code.upper()}`."
        ),
        embed=embed
    )


@bot.tree.command(name="dispatch", description="Post a dispatch update.")
@app_commands.describe(
    op_code="Example: SC-428",
    message="Dispatch update"
)
async def dispatch(interaction: discord.Interaction, op_code: str, message: str):
    guild_id = guild_id_from(interaction)
    operation = get_operation_by_code(guild_id, op_code)

    if not operation:
        await interaction.response.send_message(
            f"GHOST lookup failed. No active operation found under `{op_code.upper()}`.",
            ephemeral=True
        )
        return

    add_dispatch(
        operation_id=operation[0],
        message=message,
        author=interaction.user.display_name
    )

    embed = discord.Embed(
        title=f"GHOST DISPATCH // {op_code.upper()}",
        description=message,
        color=discord.Color.red()
    )

    embed.set_footer(
        text=f"Filed by {interaction.user.display_name} | SpacerOS Dispatch Relay"
    )

    dispatch_channel_id = get_dispatch_channel(guild_id)

    if dispatch_channel_id:
        channel = interaction.guild.get_channel(int(dispatch_channel_id))

        if channel:
            await channel.send(embed=embed)

            await interaction.response.send_message(
                f"Dispatch filed to {channel.mention}.",
                ephemeral=True
            )
            return

    await interaction.response.send_message(
        content="No dispatch channel configured. Posting dispatch here.",
        embed=embed
    )


@bot.tree.command(name="op-close", description="Close an operation.")
@app_commands.describe(op_code="Example: SC-428")
async def op_close(interaction: discord.Interaction, op_code: str):
    guild_id = guild_id_from(interaction)
    operation = get_operation_by_code(guild_id, op_code)

    if not operation:
        await interaction.response.send_message(
            f"GHOST lookup failed. No active operation found under `{op_code.upper()}`.",
            ephemeral=True
        )
        return

    close_operation(operation[0])

    await interaction.response.send_message(
        f"Operation `{op_code.upper()}` closed and archived.\n\nGHOST session terminated."
    )


bot.run(TOKEN)
