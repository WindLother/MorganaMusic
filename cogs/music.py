import discord
from discord.ext import commands 
import settings 
import wavelink

logger = settings.logging.getLogger(__name__)

class SB_Button(discord.ui.Button):
    file_name : str = None 
    
    def setup(self, data):
        self.label = data['label']
        self.custom_id = data['custom_id']
        self.file_name = data['file_name']
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        soundboard_item = await wavelink.YouTubeTrack.search(query=self.file_name, return_first=True)
        if soundboard_item:
            await self.view.player.play(soundboard_item)
        
    
class SoundboardView(discord.ui.View):
    player : wavelink.Player = None 
    
    
    @discord.ui.button(label="Stop", 
                       style=discord.ButtonStyle.red)
    async def stop_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.player.stop()
    
    def setup_buttons(self):
        # Only up to 25 buttons in total
        # with the stop button above, only 24 are possible
        buttons = [ 
               {
                "label": "Applause",
                "custom_id": "applause",
                "file_name": "https://www.youtube.com/watch?v=jDOrc8FmDy4",
            },
            {
                "label": "Announcement Jingle",
                "custom_id": "announcement",
                "file_name": "https://www.youtube.com/watch?v=V66PMeImkxI",
            },
            {
                "label": "Titanic",
                "custom_id": "titanic",
                "file_name": "https://www.youtube.com/watch?v=jg_OBEkjdcw",
            },
            {
                "label": "Deez Nuts",
                "custom_id": "deez_nuts",
                "file_name": "https://www.youtube.com/watch?v=66I78hXXwvk",
            },
            {
                "label": "Thomas Tank Engine",
                "custom_id": "thomas_tank",
                "file_name": "https://www.youtube.com/watch?v=gvTcmoJDVjg",
            },
            {
                "label": "Airhorn",
                "custom_id": "airhorn",
                "file_name": "https://www.youtube.com/watch?v=OFr74zI1LBM",
            },
            {
                "label": "Do it",
                "custom_id": "do_it",
                "file_name": "https://www.youtube.com/watch?v=z2Qe1d4urfw",
            }
        ]
        
        for button_config in buttons:
            sb_button = SB_Button()
            sb_button.setup(button_config)
            self.add_item(sb_button)
        
class MusicBot(commands.Cog):
    vc : wavelink.Player = None
    current_track = None
    music_channel = None
    history = None
    
    def __init__(self, bot):
        self.bot = bot
        self.history = list()
        
    async def setup(self):
        await wavelink.NodePool.create_node(
            bot=self.bot, 
            host="localhost",
            port=2333, 
            password="changeme"
        )
    
    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        logger.info(f"{node} is ready")
        
    
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, player: wavelink.Player, track: wavelink.Track):
        await self.music_channel.send(f"{track.title} começou a tocar")
        
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player: wavelink.Player, track: wavelink.Track, reason):
        await self.music_channel.send(f"{track.title} música finalizada")
        self.history.append(track.title)

    @commands.command(brief="Faça o bot entrar manualmente num canal de voz")
    async def join(self, ctx):
        channel = ctx.message.author.voice.channel
        self.music_channel = ctx.message.channel
        if not channel:
            embed = discord.Embed(title=":warning: Erro", description="Você precisa entrar num canal de voz antes.",
                                  color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        self.vc = await channel.connect(cls=wavelink.Player)
        embed = discord.Embed(title=":white_check_mark: Sucesso", description=f"Entrei em {channel.name}",
                              color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(brief="Busca por uma música no YouTube")
    async def add(self, ctx, *title: str):
        chosen_track = await wavelink.YouTubeTrack.search(query=" ".join(title), return_first=True)
        if chosen_track:
            self.current_track = chosen_track
            embed = discord.Embed(title=":musical_note: Música adicionada",
                                  description=f"Adicionado {chosen_track.title} na fila", color=discord.Color.green())
            await ctx.send(embed=embed)
            self.vc.queue.put(chosen_track)
        else:
            embed = discord.Embed(title=":warning: Erro", description="Não foi possível encontrar a música.",
                                  color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command(brief="Toca a faixa atual")
    async def play(self, ctx):
        if self.current_track and self.vc:
            await self.vc.play(self.current_track)
            embed = discord.Embed(title=":notes: Tocando agora", description=self.current_track.title,
                                  color=discord.Color.green())
            await ctx.send(embed=embed)

    @commands.command(brief="Pausa a música atual")
    async def pause(self, ctx):
        await self.vc.pause()
        embed = discord.Embed(title=":pause_button: Música pausada", color=discord.Color.dark_orange())
        await ctx.send(embed=embed)

    @commands.command(brief="Retoma a música pausada")
    async def resume(self, ctx):
        await self.vc.resume()
        embed = discord.Embed(title=":arrow_forward: Retomando a faixa atual", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(brief="Para a música atual")
    async def stop(self, ctx):
        await self.vc.stop()
        embed = discord.Embed(title=":stop_button: Música parada", color=discord.Color.red())
        await ctx.send(embed=embed)

    @commands.command(brief="Fast Forward n seconds")
    async def ff(self, ctx, seconds : int = 15):
        new_position = self.vc.position + seconds
        await self.vc.seek(new_position * 1000)
        
    @commands.command(brief="Go back n seconds")
    async def gb(self, ctx, seconds : int = 15):
        new_position = self.vc.position - seconds
        await self.vc.seek(new_position * 1000)
        
    
    @commands.command(brief="Sets the output volume")
    async def volume(self, ctx, new_volume : int = 100):
        await self.vc.set_volume(new_volume)
        
    
    @commands.command(brief="Shows any previous played songs")
    async def history(self, ctx):
        self.history.reverse()
        embed = discord.Embed(title="Song History")
        for track_item in self.history:
            track_info = track_item.split(" - ")
            embed.add_field(name=track_info[1], value=track_info[0], inline=False)
            
        await ctx.send(embed=embed)
            
    
    @commands.command(brief="Opens a soundboard with buttons")
    async def sb(self, ctx):
        view = SoundboardView(timeout=None)
        view.setup_buttons()
        view.player = self.vc
        await ctx.send("Your soundboard", view=view)
        
async def setup(bot):
    music_bot = MusicBot(bot)
    await bot.add_cog(music_bot)
    await music_bot.setup()