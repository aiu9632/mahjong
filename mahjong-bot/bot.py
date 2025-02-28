import discord
from discord.ext import commands
import sqlite3

# ボットの設定
PREFIX = "!"
TOKEN = "MTM0NDY0MDg1MzUxOTM2ODIzMw.GXIT_b.6CGS_tT6YYsoXw5q9AoTN5aI5spyNvOM3ysFok"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# データベース接続
conn = sqlite3.connect("mahjong_scores.db")
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS scores (
        player_id INTEGER,
        name TEXT,
        game_id INTEGER,
        rank INTEGER,
        score INTEGER,
        rate REAL,
        PRIMARY KEY (player_id, game_id)
    )
""")
conn.commit()

@bot.command()
async def record(ctx, game_id: int, player1: discord.Member, score1: int, 
                        player2: discord.Member, score2: int, 
                        player3: discord.Member, score3: int, 
                        player4: discord.Member, score4: int):
    
    game_record = [
        (0, player1.id, player1.name, score1),
        (1, player2.id, player2.name, score2),
        (2, player3.id, player3.name, score3),
        (3, player4.id, player4.name, score4),
    ]
    
    sorted_record = sorted(game_record, key=lambda x: (-x[3], x[0]))
    
    rank_points = {1: 15, 2: 5, 3: -5, 4: -15}
    for i, (_, player_id, name, score) in enumerate(sorted_record):
        rank = i + 1
        rate = rank_points[rank] + (score - 25000) / 1000

        c.execute("""
            INSERT INTO scores (player_id, name, game_id, rank, score, rate)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_id, game_id) DO UPDATE SET 
                rank = ?,
                score = ?,
                rate = ?
        """, (player_id, name, game_id, rank, score, rate, rank, score, rate))
    
    conn.commit()
    await ctx.send(f"✅ 戦績を記録しました！（対局ID: {game_id}）")

@bot.command()
async def game_result(ctx, game_id: int):
    c.execute("""
        SELECT name, rank, score, rate 
        FROM scores 
        WHERE game_id=? 
        ORDER BY rank
    """, (game_id,))
    results = c.fetchall()
    
    if not results:
        await ctx.send(f"📋 対局 {game_id} のデータが見つかりません。")
        return
    
    message = f"**🀄 対局 {game_id} の戦績:**\n"
    for name, rank, score, rate in results:
        message += f"🏅 {rank}位: {name} | 得点: {score} | レート: {rate:.2f}\n"
    
    await ctx.send(message)

@bot.command()
async def myscore(ctx, player: discord.Member = None):
    if player is None:
        player = ctx.author
    
    c.execute("""
        SELECT COUNT(*), SUM(rank), SUM(score) 
        FROM scores WHERE player_id=?
    """, (player.id,))
    result = c.fetchone()
    
    if not result or result[0] == 0:
        await ctx.send(f"{player.name} さんの戦績データがありません。")
        return

    total_games, total_rank, total_score = result
    avg_rank = total_rank / total_games
    avg_score = total_score / total_games
    total_rate = (2.5 * total_games - total_rank) * 10 + (total_score - 25000 * total_games) / 1000
    
    message = (
        f"**🀄 {player.name} さんの戦績:**\n"
        f"🕹️ 対局回数: {total_games}\n"
        f"🏅 順位平均: {avg_rank:.2f}\n"
        f"🎯 点数平均: {avg_score:.2f}\n"
        f"📈 総レート: {total_rate:.2f}"
    )
    await ctx.send(message)

@bot.command()
async def ranking(ctx):
    c.execute("""
        SELECT name, SUM(rank), SUM(score), COUNT(*) 
        FROM scores 
        GROUP BY player_id 
    """)
    results = c.fetchall()
    
    if not results:
        await ctx.send("まだレートが登録されていません。")
        return
    
    ranking_list = []
    for name, total_rank, total_score, total_games in results:
        total_rate = (2.5 * total_games - total_rank) * 10 + (total_score - 25000 * total_games) / 1000
        ranking_list.append((name, total_rate))
    
    ranking_list.sort(key=lambda x: -x[1])
    
    message = "**🏆 レートランキング（降順）**\n"
    for i, (name, total_rate) in enumerate(ranking_list, 1):
        message += f"{i}. {name}: {total_rate:.2f} 点\n"
    
    await ctx.send(message)

@bot.command()
async def delete_game(ctx, game_id: int):
    c.execute("DELETE FROM scores WHERE game_id=?", (game_id,))
    conn.commit()
    await ctx.send(f"✅ 対局 {game_id} のデータを削除しました。")

bot.run(TOKEN)
