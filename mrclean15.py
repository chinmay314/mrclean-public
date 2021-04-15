import os
import time

import discord
import pandas as pd
import youtube_dl
from discord.ext import commands
from discord.utils import get
from aio_timers import Timer
from dotenv import load_dotenv

load_dotenv('.env')

# from pydrive.auth import GoogleAuth
# from pydrive.drive import GoogleDrive

# global vars

client = commands.Bot(command_prefix=[".", "b", ":b:"], help_command=None)
score_A = 0
score_B = 0
team_A = []
team_B = []
mycolumns = [o.name for o in team_A] + ["A Bonus", "A Score"] + [o.name for o in team_B] + ["B Bonus", "B Score"]
score_board = pd.DataFrame(columns=mycolumns)
A_Tossups = dict.fromkeys(range(1, 28), "-")
B_Tossups = dict.fromkeys(range(1, 28), "-")

for i in range(28):
    init_scores = dict.fromkeys(mycolumns, "-")
    score_board = score_board.append(init_scores, ignore_index=True)

qNum = 1
score_board = score_board.drop([0])
name_a = "A"
name_b = "B"
tossup_player = None
trimmed_scoresheet = None
taunt = False
ignored = None
recognized = None
timer1 = None
timer2 = None


# i want to go home

class Player:
    def __init__(self, c_name, c_team, id):
        self.name = c_name
        self.tossups = 0
        self.negs = 0
        self.team = c_team
        self.tossups_heard = dict.fromkeys(range(1, 28), 0)
        self.is_subbed = False
        self.tossups_attempted = dict.fromkeys(range(1, 28), 0)
        self.id = id

    def reset(self):
        self.tossups = 0
        self.negs = 0
        self.tossups_heard = dict.fromkeys(range(1, 28), 0)
        self.tossups_attempted = dict.fromkeys(range(1, 28), 0)

    def stats(self):
        return self.name + ":" + '\n' + "Tossups:" + str(self.tossups) + '\n' + "Negs:" + str(
            self.negs) + '\n' + "Total Points:" + str((self.tossups - self.negs) * 4) + "\n" + "Tossups Attempted:" + str(
            sum(self.tossups_attempted.values())) + '\n' + "Subbed? " + str(
            self.is_subbed) + "\n" + "----------"

    def heard(self):
        return sum(self.tossups_heard.values())


# async def on_message(ctx, message):
#     if message.content.startswith('buzz'):
#         await buzz(ctx)


@client.command()
async def help(ctx):
    f = open('help.txt', 'r')
    file_contents = f.read()
    await ctx.send("```" + file_contents + "```")


@client.command(pass_context=True)
async def stats(ctx, identifier="ALL"):
    identifier = identifier.upper()
    to_return = ""
    not_found = True
    if identifier == "A":
        for player in team_A:
            to_return += player.stats() + "\n"
        await ctx.send("```" + to_return + "```")
    elif identifier == "B":
        for player in team_B:
            to_return += player.stats() + "\n"
        await ctx.send("```" + to_return + "```")

    elif identifier == "ALL":
        to_return += "Team A: " + name_a + "\n"
        for player in team_A:
            to_return += player.stats() + "\n"
        to_return += "\n" + "Team B: " + name_b + "\n"
        for player in team_B:
            to_return += player.stats() + "\n"
        await ctx.send("```" + to_return + "```")

    else:
        for player in team_A + team_B:
            if identifier == player.name.upper():
                not_found = False
                to_return += player.stats() + "\n"
        if not_found and identifier != "":
            await ctx.send("Player not found.")
        await ctx.send("```" + to_return + "```")


@client.command(pass_context=True)
async def team(ctx, c_team):
    global mycolumns
    global score_board
    global team_A
    global team_B
    for player in team_A + team_B:
        if ctx.author.display_name == player.name:
            await ctx.send("Player already in team. Please use .leave_team and then join.")
            return
    if c_team == "A" or c_team == "a":
        team_A.append(Player(ctx.author.display_name, "A", ctx.author.id))
        await ctx.send(ctx.author.display_name + " joined team A")
    elif c_team == "B" or c_team == "b":
        team_B.append(Player(ctx.author.display_name, "B", ctx.author.id))
        await ctx.send(ctx.author.display_name + " joined team B")

    mycolumns = [o.name for o in team_A] + ["A Bonus", "A Score"] + [o.name for o in team_B] + ["B Bonus", "B Score"]

    new_board = pd.DataFrame(columns=mycolumns)
    for j in range(28):
        # noinspection PyShadowingNames
        init_scores = dict.fromkeys(mycolumns, "-")
        new_board = new_board.append(init_scores, ignore_index=True)
    for column in score_board.columns:
        new_board[column] = score_board[column]
    score_board = new_board
    score_board = score_board.drop([0])


@client.command(pass_context=True)
async def leave_team(ctx):
    global team_A
    global team_B
    global score_board
    global mycolumns

    for player in team_A + team_B:
        if ctx.author.display_name == player.name:
            if player.team == "A":
                team_A.remove(player)
                await ctx.send("Player removed from team A")
            if player.team == "B":
                team_B.remove(player)
                await ctx.send("Player removed from team B")
            return
    await ctx.send("Player not in team")


@client.command(pass_context=True)
async def sub(ctx):
    global team_A
    global team_B
    for player in team_A + team_B:
        if ctx.author.display_name == player.name:
            if player.is_subbed:
                player.is_subbed = False
                await ctx.send("Player active")
            else:
                player.is_subbed = True
                await ctx.send("Player subbed")
            return


# noinspection PyUnusedLocal
@client.command(aliases=["sr"])
@commands.has_role("Volunteers")
async def score_reset(ctx):
    global score_A
    score_A = 0
    global score_B
    score_B = 0
    global team_A
    global team_B
    for player in team_A:
        player.reset()
    for player in team_B:
        player.reset()
    global score_board
    global qNum
    global mycolumns
    global A_Tossups
    global B_Tossups
    score_board = pd.DataFrame(columns=mycolumns)
    for j in range(28):
        # noinspection PyShadowingNames
        init_scores = dict.fromkeys(mycolumns, "-")
        score_board = score_board.append(init_scores, ignore_index=True)
    A_Tossups = dict.fromkeys(range(1, 28), "-")
    B_Tossups = dict.fromkeys(range(1, 28), "-")

    qNum = 1
    score_board = score_board.drop([0])

    await c(ctx)


@client.command(pass_context=True)
@commands.has_role("Volunteers")
async def team_reset(ctx):
    global team_A
    global team_B
    for player in team_A + team_B:
        player.team = None
    team_A = []
    team_B = []
    await score_reset(ctx)


@client.command(pass_context=True)
@commands.has_role("Volunteers")
async def reset(ctx):
    global name_a
    global name_b
    name_a = "A"
    name_b = "B"
    await team_reset(ctx)
    await score_reset(ctx)


@client.command(pass_context=True)
@commands.has_role("Volunteers")
async def taunt_mode(ctx):
    global taunt
    await ctx.send("Taunt mode toggled")
    taunt = not taunt


@client.event
async def on_ready():
    print("Bot is ready.")


@client.event
async def on_member_join(member):
    print(f'{member} has joined the server.')


@client.event
async def on_member_remove(member):
    print(f'{member} has left the server.')


# ADMIN VERIFICATION

cl = True


# noinspection PyUnusedLocal
@client.command(pass_context=True)
@commands.has_role("Volunteers")
async def w(ctx, type="none"):
    global cl
    global ignored
    global recognized
    global A_Tossups
    global B_Tossups

    missed = 0
    if score_board[recognized.name][qNum] != -4:
        score_board[recognized.name][qNum] = 0
    if (recognized.team == "A") and (score_board[recognized.name][qNum] != -4):
        A_Tossups[qNum] = 0
    elif score_board[recognized.name][qNum] != -4:
        B_Tossups[qNum] = 0

    if ((A_Tossups[qNum] == 0) or (A_Tossups[qNum] == -4)) and ((B_Tossups[qNum] == 0) or (B_Tossups[qNum] == -4)):
        await score(ctx)
        return

    ignored = recognized
    if type != "none":
        ignored = None
    await ctx.send("-------------------------")
    cl = True


# noinspection PyUnusedLocal
@client.command(pass_context=True)
@commands.has_role("Volunteers")
async def c(ctx):
    global cl
    global recognized
    global ignored
    recognized = None
    ignored = None
    cl = True
    await ctx.send("-------------------------")


# JOIN VOICE CHANNEL

@client.command(pass_context=True)
@commands.has_role("Volunteers")
async def join(ctx):
    # noinspection PyGlobalUndefined
    global voice
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected:
        await voice.move_to(channel)
    else:
        voice = await channel.connect()

    await ctx.send(f"Joined {channel}")


# noinspection PyShadowingNames
@client.command(pass_context=True)
@commands.has_role("Volunteers")
async def leave(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        await voice.disconnect()
        await ctx.send(f"Left {channel}")
    else:
        await ctx.send("Don't think I'm in a voice channel.")


# noinspection PyGlobalUndefined
@client.command(pass_context=True)
async def play(ctx, url=None):
    global voice
    # noinspection PyComparisonWithNone
    if url is None:
        return
    voice = get(client.voice_clients, guild=ctx.guild)
    song_there = os.path.isfile("s.mp3")
    try:
        if song_there:
            os.remove("s.mp3")
            print("Removed old song file")
    except PermissionError:
        print("Trying to delete song file but it's being played")
        await ctx.send("ERROR: Music playing")
        return
    await ctx.send("Getting everything ready now")
    voice = get(client.voice_clients, guild=ctx.guild)
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }],
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        print("Downloading audio now\n")
        ydl.download([url])
    for file in os.listdir("./"):
        if file.endswith("mp3") and file != "song.mp3":
            # noinspection PyShadowingNames
            name = file
            print(f"Renamed File: {file}")
            os.rename(file, "s.mp3")

    voice.play(discord.FFmpegPCMAudio("s.mp3"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 0.25
    # noinspection PyUnboundLocalVariable
    nname = name.rsplit("-", 2)
    await ctx.send(f"Playing: {nname[0]}")


# noinspection PyGlobalUndefined
@client.command(pass_context=True)
async def vol(ctx, v):
    v = int(v)
    global voice
    if v < 0 or v > 100:
        await ctx.send("Invalid input")
        return
    voice.source.volume = 0.4 * v / 100
    await ctx.send(voice.source.volume)


# noinspection PyGlobalUndefined,PyUnusedLocal
@client.command(pass_context=True, aliases=["b", "bz", "uzz", "z", ""])
async def buzz(ctx, url=None):
    global cl
    global voice
    global recognized
    global ignored

    if len(ctx.message.content) > 1:
        if ctx.message.content[1] != "u" and ctx.message.content[1] != "z" and ctx.message.content[1] != "b":
            return

    has_team = False

    for player in (team_A + team_B):
        if ctx.author.display_name == player.name:
            has_team = True

    if not has_team:
        await ctx.send("Join a team first.")
        return

    if (len(team_A) == 0) and (len(team_B) == 0):
        await ctx.send("Error: Teams empty")
        return

    if not cl:
        return

    for player in (team_A + team_B):
        if ctx.author.display_name == player.name:
            if player.is_subbed:
                await ctx.send("Player is a sub")
                return
            recognized = player

            if ignored is not None:
                if recognized.team == ignored.team:
                    await ctx.send("Same Team")
                    # await c(ctx)
                    return

    recognized.tossups_attempted[qNum] += 1

    # voice.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source="song.mp3"))
    voice.play(discord.FFmpegPCMAudio("song.mp3"), after=lambda e: print(f" has finished playing"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 0.07
    cl = False
    await ctx.send(ctx.author.display_name + " buzzed")
    # nname = name.rsplit("-", 2)
    # await ctx.send(f"Playing: {nname[0]}")


# noinspection PyUnusedLocal
@client.command()
@commands.has_role("Volunteers")
async def name(ctx, a, b):
    global name_a, name_b
    name_a = a
    name_b = b


@client.command()
@commands.has_role("Volunteers")
async def timer(ctx):
    global timer1
    global timer2

    await ctx.send("time starts now")

    async def warning():
        await ctx.send("5 seconds remaining")
    async def time():
        await ctx.send("time")

    timer1 = Timer(17, warning)
    timer2 = Timer(22, time)

@client.command()
@commands.has_role("Volunteers")
async def cancel(ctx):
    global timer1
    global timer2

    try:
        timer1.cancel()
    except:
        pass

    try:
        timer2.cancel()
    except:
        pass


@client.command()
@commands.has_role("Volunteers")
async def ping(ctx, n):
    for j in range(int(n)):
        await ctx.send(f'pong {round(client.latency * 1000)}')


@client.command()
@commands.has_role("Volunteers")
async def clean(ctx, amount):
    await ctx.channel.purge(limit=int(amount))
    await ctx.send("done")
    await ctx.channel.purge(limit=1)


# noinspection PyUnusedLocal
@client.command(pass_context=True, aliases=["s"])
@commands.has_role("Volunteers")
async def score(ctx):
    # noinspection PyGlobalUndefined
    global recognized
    global score_A
    global score_B
    global qNum
    global team_A
    global team_B
    global taunt
    global ignored
    global A_Tossups
    global B_Tossups

    score_board["A Score"][qNum] = score_A
    score_board["B Score"][qNum] = score_B

    if (A_Tossups[qNum] == "-" or A_Tossups[qNum] == 0 or A_Tossups[qNum] == -4) and (B_Tossups[qNum] == "-" or B_Tossups[qNum] == 0 or B_Tossups[qNum] == -4):
        for player in team_A + team_B:
            if not player.is_subbed:
                player.tossups_heard[qNum] += 1

    if (abs(score_A - score_B) > 28) and taunt is True:
        await ctx.send("<:chokecj:800241137247453194>")

    await cancel(ctx)
    await c(ctx)
    ignored = None
    qNum += 1
    if qNum<=25:
        await ctx.send("Next question: " + str(qNum))
    else:
        await ctx.send("End of round")
        await stats(ctx)
        await export(ctx)



@client.command(pass_context=True, aliases=["t"])
@commands.has_role("Volunteers")
async def tossup(ctx):
    # noinspection PyGlobalUndefined
    global recognized
    global score_A
    global score_B
    global qNum
    global team_A
    global team_B
    global A_Tossups
    global B_Tossups
    global name_a
    global name_b

    # error handling
    if recognized is None:
        await ctx.send("No team recognized.")

    if recognized.team is None:
        await ctx.send("Error: player does not have a team.")
        return

    if score_board[recognized.name][qNum] == 4:
        await ctx.send("Tossup already awarded.")
        return

    # updates score sheet
    score_board[recognized.name][qNum] = 4
    if recognized.team == "A":
        A_Tossups[qNum] = 4
    else:
        B_Tossups[qNum] = 4

    calc_score()
    score_board["A Score"][qNum] = score_A
    score_board["B Score"][qNum] = score_B

    for player in team_A + team_B:
        if not player.is_subbed:
            player.tossups_heard[qNum] += 1

    await score_check(ctx)


@client.command(pass_context=True, aliases=["bon"])
@commands.has_role("Volunteers")
async def bonus(ctx):
    # noinspection PyGlobalUndefined
    global recognized
    global score_A
    global score_B
    global qNum
    global team_A
    global team_B
    global taunt
    global ignored
    if recognized is None:
        await ctx.send("No team recognized.")
    bonus_team = recognized.team

    if score_board[recognized.name][qNum] != 4:
        await ctx.send("No tossup awarded.")
        return
    if score_board[bonus_team + " Bonus"][qNum] == 10:
        await ctx.send("Bonus already awarded.")
        return

    await cancel(ctx)
    score_board[bonus_team + " Bonus"][qNum] = 10
    calc_score()
    score_board["A Score"][qNum] = score_A
    score_board["B Score"][qNum] = score_B
    await score_check(ctx)

    if (abs(score_A - score_B) > 28) and taunt == True:
        await ctx.send("choke lol")

    await c(ctx)
    ignored = None
    qNum += 1
    if qNum<=25:
        await ctx.send("Next question: " + str(qNum))
    else:
        await ctx.send("End of round")
        await stats(ctx)
        await export(ctx)


# noinspection PyGlobalUndefined
@client.command(pass_context=True, aliases=["i"])
@commands.has_role("Volunteers")
async def interrupt(ctx):
    global recognized
    global score_A
    global score_B
    global qNum
    global team_A
    global team_B
    global A_Tossups
    global B_Tossups
    global name_a
    global name_b
    if recognized is None:
        await ctx.send("No team recognized.")

    if score_board[recognized.name][qNum] == -4:
        await ctx.send("Team already penalized.")
        return

    score_board[recognized.name][qNum] = -4
    if recognized.id == 518242380692979746:
        await ctx.send("You're trash.")
    if recognized.team == "A":
        A_Tossups[qNum] = -4
    else:
        B_Tossups[qNum] = -4

    calc_score()
    score_board["A Score"][qNum] = score_A
    score_board["B Score"][qNum] = score_B
    await score_check(ctx)
    await w(ctx)


def calc_score():
    global score_board, score_A, team_A, score_B, team_B, A_Tossups, B_Tossups
    score_A = 0
    score_B = 0
    for score in A_Tossups.values():
        if score != "-":
            if score<0:
                score_B -= score
            else:
                score_A += score
    if 10 in score_board["A Bonus"].value_counts():
        score_A += 10 * score_board["A Bonus"].value_counts()[10]

    for score in B_Tossups.values():
        if score != "-":
            if score<0:
                score_A -= score
            else:
                score_B += score
    if 10 in score_board["B Bonus"].value_counts():
        score_B += 10 * score_board["B Bonus"].value_counts()[10]

    # updates player stats
    for player in team_A + team_B:
        player.tossups = 0
        player.negs = 0
        if 4 in score_board[player.name].value_counts():
            player.tossups += score_board[player.name].value_counts()[4]
        if -4 in score_board[player.name].value_counts():
            player.negs += score_board[player.name].value_counts()[-4]

    score_board["A Score"][qNum] = score_A
    score_board["B Score"][qNum] = score_B


@client.command(aliases=["ch"])
async def score_check(ctx):
    global score_A
    global score_B
    if score_A > score_B:
        await ctx.send(name_a + " leads " + str(score_A) + " to " + str(score_B))
    elif score_B > score_A:
        await ctx.send(name_b + " leads " + str(score_B) + " to " + str(score_A))
    else:
        await ctx.send(name_a + ", " + name_b + " tied " + str(score_A) + " to " + str(score_B))


# noinspection PyShadowingNames
@client.command()
@commands.has_role("Volunteers")
async def undo(ctx, back=""):
    global score_board, qNum
    global team_A
    global team_B
    global mycolumns
    global A_Tossups
    global B_Tossups
    global score_A
    global score_B
    global ignored
    global recognized

    A_Tossups[qNum] = "-"
    B_Tossups[qNum] = "-"
    for player in team_A + team_B:
        score_board.iloc[qNum - 1][player.name] = "-"
        player.tossups_heard[qNum] = 0
        player.tossups_attempted[qNum] = 0
    score_board.iloc[qNum - 1]["A Bonus"] = "-"
    score_board.iloc[qNum - 1]["B Bonus"] = "-"
    score_board.iloc[qNum - 1]["A Score"] = "-"
    score_board.iloc[qNum - 1]["B Score"] = "-"
    await ctx.send("Cleared question " + str(qNum) + ".")

    if back == "back" and qNum > 1:
        qNum -= 1
        A_Tossups[qNum] = "-"
        B_Tossups[qNum] = "-"
        for player in team_A + team_B:
            score_board.iloc[qNum - 1][player.name] = "-"
            player.tossups_heard[qNum] = 0
            player.tossups_attempted[qNum] = 0
        score_board.iloc[qNum - 1]["A Bonus"] = "-"
        score_board.iloc[qNum - 1]["B Bonus"] = "-"
        score_board.iloc[qNum - 1]["A Score"] = "-"
        score_board.iloc[qNum - 1]["B Score"] = "-"
        await ctx.send("Cleared question " + str(qNum) + ".")
    calc_score()
    for i in range(qNum - 1, 27):
        score_board.iloc[i]["A Score"] = "-"
        score_board.iloc[i]["B Score"] = "-"
    await c(ctx)
    ignored = None


@client.command(aliases=["ss"])
@commands.has_role("Volunteers")
async def score_sheet(ctx):
    global score_board, name_a, name_b, A_Tossups, B_Tossups, trimmed_scoresheet
    await ctx.send("Team A - " + name_a + "    Team B - " + name_b)
    trimmed_scoresheet = score_board[["A Bonus", "A Score", "B Bonus", "B Score"]]
    trimmed_scoresheet.insert(loc=0, column="A TU", value=pd.Series(A_Tossups))
    trimmed_scoresheet.insert(loc=3, column="B TU", value=pd.Series(B_Tossups))
    trimmed_scoresheet = trimmed_scoresheet.drop([26])
    trimmed_scoresheet = trimmed_scoresheet.drop([27])
    await ctx.send("```" + str(trimmed_scoresheet) + "```")


@client.command()
@commands.has_role("Volunteers")
async def export(ctx, sheet="overall"):
    global score_board, team_A, team_B
    global team_A
    global team_B
    for player in team_A + team_B:
        score_board.iloc[25][player.name] = "TU Heard"
        score_board.iloc[26][player.name] = player.heard()
    if sheet == "overall":
        score_board.to_excel("scoresheet.xlsx")
        await ctx.send(file=discord.File('scoresheet.xlsx'))
    else:
        # noinspection PyUnresolvedReferences
        trimmed_scoresheet.to_excel("team_scores.xlsx")
        await ctx.send(file=discord.File('team_scores.xlsx'))


    client.run(os.getenv('TOKEN15')) # 15
