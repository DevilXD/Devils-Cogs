import discord
import datetime
import os
import asyncio
import re
from discord.ext import commands
from cogs.utils import checks
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import box, pagify, escape_mass_mentions
from random import choice

__author__ = "DevilXD"

class Counting:
    """Because who doesn't like to kill time?"""

    def __init__(self, bot):
        self.bot = bot
        self.set = dataIO.load_json('data/counting/settings.json')
        self.shield = []

    def __unload(self):
        self.save()

    def save(self):
        dataIO.save_json('data/counting/settings.json', self.set)

    def server_init(self,server):
        self.set[server.id] = {
            "channels": {},
        }

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(administrator=True)
    async def count(self, ctx):
        """Because who doesn't like to kill time?"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @count.command(pass_context=True)
    async def add(self, ctx, channel : discord.Channel):
        """Makes the channel a counting channel."""
        
        server = ctx.message.server
        if server.id not in self.set:
            self.server_init(server)
            await self.bot.say("Server initialized!")
        if channel.id in self.set[server.id]["channels"]:
            await self.bot.say(":x: This channel is already a counting channel!")
            return
        self.set[server.id]["channels"][channel.id] = {"last": None, "count": 0, "goal": 0, "strict": False}
        self.save()
        await self.bot.edit_channel(channel,topic = "Next message must start with 1")
        await self.bot.say("Channel added!")

    @count.command(pass_context=True)
    async def remove(self, ctx, channel : discord.Channel):
        """Free's up the channel."""
        
        server = ctx.message.server
        if server.id not in self.set:
            await self.bot.say(":x: Uninitialized server!")
            return
        if channel.id not in self.set[server.id]["channels"]:
            await self.bot.say(":x: This is not a counting channel!")
            return
        del self.set[server.id]["channels"][channel.id]
        self.save()
        await self.bot.edit_channel(channel,topic = None)
        await self.bot.say("Channel removed!")

    @count.command(pass_context=True, name="set")
    async def _set(self, ctx, channel : discord.Channel, count : int):
        """Sets the current count in a channel."""
        
        server = ctx.message.server
        if server.id not in self.set:
            await self.bot.say(":x: Uninitialized server!")
            return
        if channel.id not in self.set[server.id]["channels"]:
            await self.bot.say(":x: This is not a counting channel!")
            return
        self.set[server.id]["channels"][channel.id]["count"] = count
        self.set[server.id]["channels"][channel.id]["last"] = None
        self.save()
        await self.bot.edit_channel(channel,topic = "Next message must start with {}".format(count+1))
        await self.bot.say("Channel count set to {}!".format(count))

    @count.command(pass_context=True)
    async def strict(self, ctx, channel : discord.Channel):
        """Toggles the 'strict mode' for a counting channel."""
        
        server = ctx.message.server
        if server.id not in self.set:
            await self.bot.say(":x: Uninitialized server!")
            return
        if channel.id not in self.set[server.id]["channels"]:
            await self.bot.say(":x: This is not a counting channel!")
            return
        self.set[server.id]["channels"][channel.id]["strict"] = not self.set[server.id]["channels"][channel.id]["strict"]
        self.save()
        await self.bot.say("Strict mode set to {} for this server!".format(self.set[server.id]["channels"][channel.id]["strict"]))

    @count.command(pass_context=True)
    async def goal(self, ctx, channel : discord.Channel, goal : int):
        """Adds a goal to a channel. Set to 0 to remove."""
        
        server = ctx.message.server
        if server.id not in self.set:
            await self.bot.say(":x: Uninitialized server!")
            return
        if channel.id not in self.set[server.id]["channels"]:
            await self.bot.say(":x: This is not a counting channel!")
            return
        self.set[server.id]["channels"][channel.id]["goal"] = goal
        self.save()
        current_count = self.set[server.id]["channels"][channel.id]["count"]
        if goal > 0:
            await self.bot.edit_channel(channel,topic = "Next message must start with {} | Reach {} to complete.".format(current_count+1,goal))
        else:
            await self.bot.edit_channel(channel,topic = "Next message must start with {}".format(current_count+1))
        await self.bot.say("Channel goal set to {}!".format(goal))
    
    async def respond(self,message,response):
        if message.author.id not in self.shield:
            self.shield.append(message.author.id)
        await self.bot.delete_message(message)
        msg = await self.bot.send_message(message.channel,response)
        await asyncio.sleep(5)
        try:
            await self.bot.delete_message(msg)
        except:
            pass

    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return
        if message.server is None or message.server.id not in self.set:
            return
        server = message.server
        if message.channel.id not in self.set[server.id]["channels"]:
            return
        channel = message.channel
        if self.set[server.id]["channels"][channel.id]["strict"] and self.set[server.id]["channels"][channel.id]["last"] == message.author.id:
            await self.respond(message,"{} You can't send two messages in a row to this channel!".format(message.author.mention))
            return
        content = message.content
        
        current_count = self.set[server.id]["channels"][channel.id]["count"]
        current_goal = self.set[server.id]["channels"][channel.id]["goal"]
        if current_goal > 0 and current_count > current_goal:
            return
        next_count = current_count + 1
        has_next_count = re.search(r"^{}(?: .*)?$".format(next_count),content)
        if has_next_count:
            #Allow:
            current_count = next_count
            self.set[server.id]["channels"][channel.id]["count"] = current_count
            self.set[server.id]["channels"][channel.id]["last"] = message.author.id
            if current_count == current_goal:
                overwrite = discord.PermissionOverwrite()
                overwrite.send_messages = False
                role = discord.utils.get(server.roles, id=server.id)
                await self.bot.edit_channel_permissions(channel, role, overwrite)
                await self.bot.send_message(channel,"Congratulations, this channel has reached it's goal of {} :tada::tada::tada:".format(current_goal))
                return
            if current_goal > 0:
                await self.bot.edit_channel(channel,topic = "Next message must start with {} | Reach {} to complete.".format(next_count+1,current_goal))
            else:
                await self.bot.edit_channel(channel,topic = "Next message must start with {}".format(next_count+1))
            if next_count % 10 == 0:
                self.save()
        else:
            #Deny:
            await self.respond(message,"{} Your message needs to start with {}".format(message.author.mention,next_count))

    async def on_message_edit(self, msg_before, msg_after):
        if msg_after.author.id == self.bot.user.id:
            return
        if msg_after.server.id not in self.set:
            return
        server = msg_after.server
        if msg_after.channel.id not in self.set[server.id]["channels"]:
            return
        channel = msg_after.channel
        before_content = msg_before.content
        after_content = msg_after.content
        
        match = re.search(r"^(\d+)(?: .*)?$", before_content)
        if match:
            before_count = match.group(1)
        else:
            before_count = 0
        match = re.search(r"^(\d+)(?: .*)?$", after_content)
        if match:
            after_count = match.group(1)
        else:
            after_count = 0
        still_has_correct_count = before_count == after_count
        if still_has_correct_count:
            #Allow:
            pass
        else:
            #Deny:
            if msg_after.author.id not in self.shield:
                self.shield.append(msg_after.author.id)
            await self.bot.delete_message(msg_after)
            msg = await self.bot.send_message(channel,"{} You are sneaky, but I saw it :eyes: Seems like you don't want to play by the rules...".format(msg_after.author.mention))
            overwrite = discord.PermissionOverwrite()
            overwrite.send_messages = False
            await self.bot.edit_channel_permissions(channel, msg_after.author, overwrite)
            await asyncio.sleep(30)
            overwrite = discord.PermissionOverwrite()
            overwrite.read_messages = False
            await self.bot.edit_channel_permissions(channel, msg_after.author, overwrite)
            await self.bot.delete_message(msg)

    async def on_message_delete(self, message):
        if message.author.id == self.bot.user.id:
            return
        if message.server.id not in self.set:
            return
        server = message.server
        if message.channel.id not in self.set[server.id]["channels"]:
            return
        channel = message.channel
        
        #Shield:
        if message.author.id in self.shield:
            self.shield.remove(message.author.id)
            return
        
        #Deny:
        msg = await self.bot.send_message(channel,"{} You are sneaky, but I saw it :eyes: Seems like you don't want to play by the rules...".format(message.author.mention))
        overwrite = discord.PermissionOverwrite()
        overwrite.send_messages = False
        await self.bot.edit_channel_permissions(channel, message.author, overwrite)
        await asyncio.sleep(30)
        overwrite = discord.PermissionOverwrite()
        overwrite.read_messages = False
        await self.bot.edit_channel_permissions(channel, message.author, overwrite)
        await self.bot.delete_message(msg)

def check_folders():
    paths = ["data/counting"]
    for path in paths:
        if not os.path.exists(path):
            print("Creating {} folder...".format(path))
            os.makedirs(path)

def check_files():
    f = "data/counting/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default settings.json...")
        dataIO.save_json(f, {})

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Counting(bot))
