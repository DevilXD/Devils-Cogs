import os
import discord
import asyncio
from cogs.utils import checks
from discord.ext import commands
from random import choice, randint
from cogs.utils.dataIO import dataIO

class InviteUtils:
    def __init__(self, bot):
        self.bot = bot
        self.set = dataIO.load_json('data/inviteutils/settings.json')
        self.joinmessage_color = 65280
        self.leavemessage_color = 16711680
        self.reaction_yes = '\u2705'
        self.reaction_no = '\u274C'
        self.load_task = self.bot.loop.create_task(self.on_load_tasks())

    def __unload(self):
        self.load_task.cancel()

    def save(self):
        dataIO.save_json('data/inviteutils/settings.json', self.set)

    def reload(self):
        self.set = dataIO.load_json('data/inviteutils/settings.json')

    def server_init(self, server):
        self.set[server.id] = {
            "channel": None,
            "embed": False,
            "joinmessage": "{0.mention} has joined!",
            "leavemessage": "{0.mention} has left!",
            "join": False,
            "leave": False,
            "botrole": None,
            "invites": {},
        }

    async def on_load_tasks(self):
        await self.bot.wait_until_ready()
        for server in self.bot.servers:
            await self.inv_update(server)

    async def inv_update(self, server):
        if server.id not in self.set:
            return
        try:
            invites = await self.bot.invites_from(server)
        except:
            return
        invite_urls = []
        for inv in invites:
            if inv.url not in self.set[server.id]["invites"]:
                self.set[server.id]["invites"][inv.url] = {"uses": inv.uses}
            else:
                self.set[server.id]["invites"][inv.url]["uses"] = inv.uses    # sync uses
            invite_urls.append(inv.url)
        for inv_url in list(self.set[server.id]["invites"]):
            if inv_url not in invite_urls:
                del self.set[server.id]["invites"][inv_url]                   # clean up database
        self.save()

    async def confirm_msg(self, ctx,  e: discord.Embed, timeout: int):
        server = ctx.message.server
        author = ctx.message.author
        e.set_author(name=server.name, icon_url=server.icon_url)
        e.set_footer(text="Use the reactions to confirm changes.")
        try:
            msg = await self.bot.say(embed=e)
        except:
            await self.bot.say("Was unable to embed a message. Need EMBED_LINKS permission.")
            return False
        try:
            await self.bot.add_reaction(msg, self.reaction_yes)
            await self.bot.add_reaction(msg, self.reaction_no)
        except:
            self.bot.say("Was unable to add reactions. Need ADD_REACTIONS permission.")
            return False
        decision = await self.bot.wait_for_reaction(message=msg, user=author, emoji=[self.reaction_yes, self.reaction_no], timeout=timeout or 60)
        if server.me.server_permissions.manage_messages:
            await self.bot.clear_reactions(msg)
        else:
            await self.bot.say("Was unable to clear reactions. Need MANAGE_MESSAGES permission.")
        if decision is None or decision.reaction.emoji != self.reaction_yes:
            e.set_footer(text="{} Canceled by {}".format(self.reaction_no, decision and author.name + "#" + author.discriminator or "(timed out)"))
            await self.bot.edit_message(msg,embed=e)
            return False
        elif decision.reaction.emoji == self.reaction_yes:
            e.set_footer(text="{} Confirmed by {}".format(self.reaction_yes, decision and author.name + "#" + author.discriminator or "(unknown)"))
            await self.bot.edit_message(msg,embed=e)
            return True
        await self.bot.say("Confirm_msg module error.")
        return False

    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def invutils(self, ctx):
        """Customize your inviting experience."""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @invutils.command(pass_context=True)
    async def examples(self, ctx):
        """Shows some examples for the messages."""
        msg = """You can customize your join/leave messages as follows:
    {0} is the user.
    {1} is the server.
    {2} is the invite.
    {3} is the role.
Example formats:
    {0.mention} - mention the user.
    {0.name}    - say the user's name.
    {0.id}      - user's ID.
    {1.name}    - name of the server
    {2.inviter} - name of the user that made the invite.
    {2.url}     - the invite link the user joined with.
    {2.code}    - the 'code' part of the invite
    {3.name}    - the name of the role being assigned on join.
Message Examples:
    join:
        Hey {0.mention}, welcome to {2.name}! You have been assigned to {3.name}. I hope you enjoy your stay!
        User {0.mention} joined with {1.url}, referred by {1.inviter}. Welcome to {2.name}!
    leave:
        {0.name} has just left {1.name}! Bye {0.name}, hope you had a good stay!"""
        await self.bot.say("**Here are some examples!**\n\n" + "```css\n" + msg + "```")

    @invutils.command(pass_context=True)
    async def info(self, ctx):
        """Shows the current InviteUtils settings for this server."""
        server = ctx.message.server
        if server.id not in self.set:
            self.server_init(server)
        e = discord.Embed()
        role = discord.utils.get(server.roles, id=self.set[server.id]["botrole"])
        channel = self.bot.get_channel(self.set[server.id]["channel"])
        c = 0
        for inv in self.set[server.id]["invites"]:
            if "role" in self.set[server.id]["invites"][inv]:
                c+=1
        e.set_author(name="Settings for " + server.name, icon_url=server.icon_url)
        e.add_field(name="Channel:", value="#" + channel.name if channel else None)
        e.add_field(name="Join Message Enabled:", value=self.set[server.id]["join"])
        e.add_field(name="Leave Message Enabled:", value=self.set[server.id]["leave"])
        e.add_field(name="Bot Role:", value=role.name if role else None)
        e.add_field(name="Embed", value=self.set[server.id]["embed"])
        e.add_field(name="Role-invite links:", value=c)
        e.add_field(name="Join Message:", value=self.set[server.id]["joinmessage"], inline=False)
        e.add_field(name="Leave Message:", value=self.set[server.id]["leavemessage"], inline=False)
        try:
            await self.bot.say(embed=e)
        except Exception as e:
            await self.bot.say(e)
        await self.inv_update(server)

    @invutils.command(pass_context=True)
    async def channel(self, ctx, *, channel: discord.Channel):
        """Sets the channel for the welcome/leave messages. Set to 'none' to disable."""
        server = ctx.message.server
        if channel is None or channel not in self.bot.get_all_channels():
            await self.bot.say("That channel doesn't seem to exist - I can't see it!")
            return
        if server.me.permissions_in(channel).send_messages:
            if server.id not in self.set:
                self.server_init(server)
            self.set[server.id]['channel'] = channel.id
            await self.bot.say("Channel has been set to {}.".format(channel.mention))
            self.save()
        else:
            await self.bot.say("I don't have the `send_messages` permission in {}.".format(channel.mention))

    @invutils.command(pass_context=True)
    async def joinmessage(self, ctx, *, message: str):
        """Sets the 'join' message."""
        server = ctx.message.server
        if server.id not in self.set:
            self.server_init(server)
        self.set[server.id]['joinmessage'] = message
        await self.bot.say("Join message has been set.")
        self.save()

    @invutils.command(pass_context=True)
    async def leavemessage(self, ctx, *, message: str):
        """Sets the 'leave' message."""
        server = ctx.message.server
        if server.id not in self.set:
            self.server_init(server)
        self.set[server.id]['leavemessage'] = message
        await self.bot.say("Leave message has been set.")
        self.save()

    @invutils.command(pass_context=True)
    async def botrole(self, ctx, *, role_name: str):
        """Sets the role to be added to bots on join. Set to 'none' to disable."""
        server = ctx.message.server
        if server.id not in self.set:
            self.server_init(server)
        if role_name.lower().strip() != "none":
            role = discord.utils.get(server.roles, name=role_name)
            if role is None:
                await self.bot.say("That role doesn't seem to exist.")
                return
        else:
            role = discord.Role(name = "none", id = 0, position = 0, server=server)
        if ctx.message.author.server_permissions.manage_roles and server.me.server_permissions.manage_roles and server.me.top_role > role:
            if role.name != "none":
                self.set[server.id]['botrole'] = role.id
                await self.bot.say("The bot role has been set.")
            else:
                self.set[server.id]['botrole'] = None
                await self.bot.say("The bot role has been disabled.")
            self.save()
        elif not ctx.message.author.server_permissions.manage_roles:
            await self.bot.say("You do not have the MANAGE_ROLES permission!")
        elif not server.me.server_permissions.manage_roles:
            await self.bot.say("I do not have the MANAGE_ROLES permission!")
        elif server.me.top_role <= role:
            await self.bot.say("That role is higher or equal with my highest role - I can't assign that!")

    @invutils.command(pass_context=True)
    async def embed(self, ctx):
        """Toggles between text or embeds."""
        server = ctx.message.server
        channel = discord.utils.get(self.bot.get_all_channels(), id=self.set[server.id]["channel"])
        if server.id not in self.set or channel is None:
            await self.bot.say(":x: **There's nothing to toggle just yet. Try setting a channel first.**")
            return
        if not server.me.permissions_in(channel).embed_links:
            await self.bot.say("Was unable to embed a message. Need EMBED_LINKS permission.")
            return
        self.set[server.id]["embed"] = not self.set[server.id]["embed"]     # toggle
        if self.set[server.id]["embed"] is True:
            await self.bot.say("Messages will now be embedded.")
        else:
            await self.bot.say("Messages will no longer be embedded.")
        self.save()

    @invutils.command(pass_context=True)
    async def togglej(self, ctx):
        """Enable/disable the join message."""
        server = ctx.message.server
        if server.id not in self.set:
            await self.bot.say(":x: **There's nothing to toggle just yet. Try setting a channel first.**")
            return
        self.set[server.id]["join"] = not self.set[server.id]["join"]       # toggle
        if self.set[server.id]["join"] is True:
            await self.bot.say("Join messages are now enabled.")
        else:
            await self.bot.say("Join messages are now disabled.")
        self.save()

    @invutils.command(pass_context=True)
    async def togglel(self, ctx):
        """Enable/disable the leave message."""
        server = ctx.message.server
        if server.id not in self.set:
            await self.bot.say(":x: **There's nothing to toggle just yet. Try setting a channel first.**")
            return
        self.set[server.id]["leave"] = not self.set[server.id]["leave"]
        if self.set[server.id]["leave"] is False:
            await self.bot.say("Leave messages are now enabled.")
        else:
            await self.bot.say("Leave messages are now disabled.")
        self.save()

    @invutils.command(pass_context=True)
    async def addrole(self, ctx, invite: str, *, rolename: str):
        """Bind a role to an invite (will be added on join)."""
        server = ctx.message.server
        if server.id not in self.set:
            self.server_init(server)
        role = discord.utils.get(server.roles, name=rolename)
        if role is None:
            await self.bot.say("That role doesn't seem to exist.")
            return
        if server.me.top_role <= role:
            await self.bot.say("That role is higher or equal with my highest role - I can't assign that!")
            return
        try:
            invites = await self.bot.invites_from(server)
        except:
            await self.bot.say("There is no invites on this server.")
            return
        if invite.startswith("https://discord.gg/") or invite.startswith("http://discord.gg/"):
            tmp = invite.split('/')
            invite = tmp[3]
        await self.inv_update(server)   # make sure we're working on updated database
        for inv in invites:
            tmp = inv.url.split('/')
            if tmp[3] == invite and inv.url in self.set[server.id]["invites"]:
                if "role" in self.set[server.id]["invites"][inv.url]:
                    prev_role = discord.utils.get(server.roles, id=self.set[server.id]["invites"][inv.url]["role"])
                    if prev_role is not None:
                        e = discord.Embed(description="This invite already has a role assigned to it. Replace?")
                        e.add_field(name="Invite", value=inv.url, inline=False)
                        e.add_field(name="Current Role", value=prev_role.name, inline=True)
                        e.add_field(name="Replacing Role", value=role.name, inline=True)
                        confirm = await self.confirm_msg(ctx, e, 60)
                        if confirm is False:
                            return
                self.set[server.id]["invites"][inv.url]["role"] = role.id
                await self.bot.say("The `{}` role is now bound to the `{}` invite.".format(role.name, invite))
                self.save()
                return
        await self.bot.say("That invite doesn't seem to exist.")

    @invutils.command(pass_context=True)
    async def removerole(self, ctx, invite: str):
        """Unbind a role from an invite."""
        server = ctx.message.server
        if server.id not in self.set:
            self.server_init(server)
        if invite.startswith("https://discord.gg/") or invite.startswith("http://discord.gg/"):
            tmp = invite.split('/')
            invite = "http://discord.gg/" + tmp[3]
        else:
            invite = "http://discord.gg/" + invite
        if invite not in self.set[server.id]["invites"] or "role" not in self.set[server.id]["invites"][invite]:
            await self.bot.say("That invite doesn't seem to have any roles assigned to it.")
            return
        role = discord.utils.get(server.roles, id=self.set[server.id]["invites"][invite]["role"])
        if role is None:
            role = discord.Role(name="deleted-role", id=0, position=0, server=server)
        e = discord.Embed(description="You are about to delete a role-invite link:")
        e.add_field(name="Invite", value=invite, inline=False)
        e.add_field(name="Role", value=role.name, inline=False)
        confirm = await self.confirm_msg(ctx, e, 60)
        if confirm is True:
            try:
                del self.set[server.id]["invites"][invite]["role"]
                await self.bot.say("The link has been removed, users won't get {} role anymore when joining with this invite.".format(role.name))
            except:
                await self.bot.say("Failed to unbind the role from the invite.")
            self.save()

    @invutils.command(pass_context=True)
    async def list(self, ctx):
        """List all invites with roles bound to them."""
        server = ctx.message.server
        if server.id not in self.set:
            self.server_init(server)
        msg = ""
        for inv in self.set[server.id]["invites"]:
            if "role" in self.set[server.id]["invites"][inv]:
                role = discord.utils.get(server.roles, id=self.set[server.id]["invites"][inv]["role"])
                if role is None:
                    role = discord.Role(name="deleted-role", id=0, position=0, server=server)
                tmp = inv.split('/')
                n = max(8 - len(tmp[3]), 0)
                spaces = ' ' * n
                msg = msg + "{}{} : {}".format(tmp[3], spaces, role.name) + "\n"
        if msg != "":
            await self.bot.say("List of invites with roles attached to them:\n```\nInvite   : Role\n" + msg + "```")
        else:
            await self.bot.say("There's no invites with roles bound to them on this server!")

    @invutils.command(pass_context=True)
    async def disable(self, ctx):
        """Deletes all settings for the current server."""
        server = ctx.message.server
        if server.id not in self.set:
            await self.bot.say(":x: **InviteUtils was never enabled on this server.**")
            return
        e = discord.Embed(description="You are about to delete all settings for this server.\nDo you really want to do it?")
        confirm = await self.confirm_msg(ctx, e, 60)
        if confirm is True:
            del self.set[server.id]
            self.save()
            await self.bot.say("Successfully deleted all settings for this server.")

    

    async def on_member_join(self, member):
        server = member.server
        if server.id not in self.set:
            return
        channel = self.set[server.id]["channel"]
        joinmessage = self.set[server.id]["joinmessage"]
        json_list = self.set[server.id]["invites"]
        if json_list is None:
            return
        try:
            invites = await self.bot.invites_from(server)
        except:
            await self.bot.say("There is no invites on this server.")
            return
        role = discord.Role(name="None", id=0, position=0, server=server)
        if member.bot and self.set[server.id]["botrole"] is not None:
            role = discord.utils.get(server.roles, id=self.set[server.id]["botrole"])
            if role is not None:
                await asyncio.sleep(3)
                await self.bot.add_roles(member, role)
        await asyncio.sleep(1)
        invite = None
        determined = False
        for inv in invites:
            if inv.url in json_list and int(inv.uses) == int(json_list[inv.url]["uses"])+1:
                if "role" in json_list[inv.url]:
                    role = discord.utils.get(server.roles, id=json_list[inv.url]["role"])
                    if role is not None:
                        await asyncio.sleep(3)
                        await self.bot.add_roles(member, role)
                if invite is None:
                    invite = inv    #found it!
                    determined = True
                else:
                    determined = False
            elif inv.url not in json_list and int(inv.uses) == 1:      #looks like we don't have that invite in the database yet but somebody just used it
                if invite is None:
                    invite = inv    #found it!
                    determined = True
                else:
                    determined = False
        if self.set[server.id]["join"] is True and channel is not None and joinmessage is not None:
            if invite is None or determined is False: #couldn't determine the correct invite, switching to default
                invite = discord.Invite(server=server, url="Unknown", inviter={"name": "Unknown", "discriminator": "0000", "id": 0}, code="Unknown", uses="Unknown", max_uses="Unknown")
            if self.set[server.id]["embed"]:
                try:
                    e = discord.Embed(title="Member Joined!", description=joinmessage.format(member, server, invite, role), color=self.joinmessage_color)
                    e.set_thumbnail(url=member.avatar_url)
                    await self.bot.send_message(server.get_channel(channel), embed=e)
                except discord.Forbidden:
                    await self.bot.send_message(server.get_channel(channel), "Was unable to embed a message. Need EMBED_LINKS permissions.")
                    await self.bot.send_message(server.get_channel(channel), joinmessage.format(member, server, invite, role))
                except Exception as e:
                    await self.bot.send_message(server.get_channel(channel), "Your `joinmessage` was improperly formatted!:\n{}".format(e))
            else:
                try:
                    await self.bot.send_message(server.get_channel(channel), joinmessage.format(member, server, invite, role))
                except Exception as e:
                    await self.bot.send_message(server.get_channel(channel), "Your `joinmessage` was improperly formatted!:\n{}".format(e))
            if determined is False:
                await self.bot.send_message(server.get_channel(channel), """The correct invite the last user joined with couldn't be determined, possible causes are:
```
1. The user joined with an invite that had limited uses and it just ran out of uses.
2. The user that joined was a bot authorized by the OAuth2 system instead of the standard invite.
3. The database wasn't synced properly - probably because the bot wasn't online when the last user joined.
Tip: Checking settings for the current server syncs the database. (info)
```""")
        await self.inv_update(server)

    async def on_member_remove(self, member):
        server = member.server
        if server.id not in self.set or self.set[server.id]["leave"] is False:
            return
        channel = self.set[server.id]["channel"]
        leavemessage = self.set[server.id]["leavemessage"]
        if channel is None or leavemessage is None:
            return
        if self.set[server.id]["embed"]:
            try:
                e = discord.Embed(title="Member Left!", description=leavemessage.format(member, server), color=self.leavemessage_color)
                e.set_thumbnail(url=member.avatar_url)
                await self.bot.send_message(server.get_channel(channel), embed=e)
            except discord.Forbidden:
                await self.bot.say("Was unable to embed a message. Need EMBED_LINKS permissions.")
                await self.bot.send_message(server.get_channel(channel), leavemessage.format(member, server))
            except:
                await self.bot.say("Your `leavemessage` was improperly formatted!")
        else:
            await self.bot.send_message(server.get_channel(channel), leavemessage.format(member, server))
        await self.inv_update(server)

def check_folder():
    if not os.path.exists('data/inviteutils'):
        print('Creating data/inviteutils folder...')
        os.makedirs('data/inviteutils')

def check_file():
    f = 'data/inviteutils/settings.json'
    if not dataIO.is_valid_json(f):
        print('Creating default settings.json...')
        dataIO.save_json(f, {})

def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(InviteUtils(bot))
