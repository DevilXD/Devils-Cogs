import discord
import asyncio
from discord.ext import commands
from cogs.utils import checks

class GlobalRole:

    def __init__(self, bot):
        self.bot = bot
        self.stop = False
        self.busy = False
        self.reaction_yes = '\u2705'
        self.reaction_no = '\u274C'

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
    async def globalrole(self, ctx, operation: str, *, role: str=None):
        """Add or remove a role from all members. Use 'add', 'remove' or 'stop' as operations.
        Examples:
        globalrole add All          - adds the All role to all members
        globalrole remove Other     - removes the Other role from all members
        globalrole add Other;All    - adds the Other role to all members with the All role
        globalrole remove All;Other - removes the All role from all members with the Other role
        globalrole stop             - stops the current operation"""
        valid_operations = ["add", "remove", "stop"]
        server = ctx.message.server
        author = ctx.message.author
        channel = ctx.message.channel
        operation = operation.lower()
        if operation not in valid_operations:
            list_str = ", ".join(valid_operations)
            await self.bot.say("Invalid operation! Valid operations are:\n```\n" + list_str + "\n```")
            return
        if operation == "stop":
            self.stop = self.busy
            if self.stop == True:
                await self.bot.say("Stopping...")
            else:
                await self.bot.say("There are no operations running right now!")
            return
        if self.busy == True:
            await self.bot.say("Operation already running - check the last message for progress!\nUse `[p]globalrole stop` to stop the current operation.")
            return
        if role is None:
            await self.bot.send_cmd_help(ctx)
            return
        frole = None
        if ';' in role:
            role = role.split(';')
            if len(role) > 2:
                await self.bot.send_cmd_help(ctx)
                return
            frole = role[1]
            role = role[0]
        role = discord.utils.get(server.roles, name=role)
        if role is None:
            await self.bot.say("That role doesn't seem to exist!")
            return
        if not server.me.server_permissions.manage_roles:
            await self.bot.say("I don't have the MANAGE_ROLES permission!")
            return
        if role >= author.top_role:
            await self.bot.say("That role is higher or equal with your highest role - You can't manage that!")
            return
        if role >= server.me.top_role:
            await self.bot.say("That role is higher or equal with my highest role - I can't manage that!")
            return
        if frole is not None:
            frole = discord.utils.get(server.roles, name=frole)
            if frole is None:
                await self.bot.say("That role doesn't seem to exist!")
                return
        if operation == "add":
            if frole is None:
                text = "Adding `{}` role to all server members... ({}/{})"
                desc = "You are about to add the `{}` role to all server members. Proceed?".format(role.name)
            else:
                text = "Adding `{}` role to all server members with `{}` role... ({}/{})"
                desc = "You are about to add the `{}` role to all server members with the `{}` role. Proceed?".format(role.name, frole.name)
        elif operation == "remove":
            if frole is None:
                text = "Removing `{}` role from all server members... ({}/{})"
                desc = "You are about to remove the `{}` role from all server members. Proceed?".format(role.name)
            else:
                text = "Removing `{}` role from all server members with `{}` role... ({}/{})"
                desc = "You are about to remove the `{}` role from all server members with the `{}` role. Proceed?".format(role.name, frole.name)
        e = discord.Embed(description=desc)
        confirm = await self.confirm_msg(ctx, e, 60)
        if confirm is False:
            return
        count = 0
        proc_count = 0
        member_count = len(server.members)
        if frole is None:
            msg = await self.bot.say(text.format(role.name, count, member_count))
        else:
            msg = await self.bot.say(text.format(role.name, frole.name, count, member_count))
        self.busy = True
        for member in server.members:
            if operation == "add" and role not in member.roles:
                if frole is None:
                    await self.bot.add_roles(member, role)
                    proc_count += 1
                elif frole in member.roles:
                    await self.bot.add_roles(member, role)
                    proc_count += 1
            elif operation == "remove" and role in member.roles:
                if frole is None:
                    await self.bot.remove_roles(member, role)
                    proc_count += 1
                elif frole in member.roles:
                    await self.bot.remove_roles(member, role)
                    proc_count += 1
            count += 1
            if count % 100 == 0 or proc_count >= 10:
                proc_count = 0
                try:
                    if frole is None:
                        msg = await self.bot.edit_message(msg, new_content=text.format(role.name, count, member_count))
                    else:
                        msg = await self.bot.edit_message(msg, new_content=text.format(role.name, frole.name, count, member_count))
                except:
                    if frole is None:
                        msg = await self.bot.say(text.format(role.name, count, member_count))
                    else:
                        msg = await self.bot.say(text.format(role.name, frole.name, count, member_count))
                member_count = len(server.members)
            if self.stop == True:
                break
        self.busy = False
        if msg is not None:
            await self.bot.delete_message(msg)
        if self.stop == True:
            await self.bot.say("Operation aborted by the user! ({}/{})".format(count, member_count))
            self.stop = False
            return
        if operation == "add":
            if frole is None:
                await self.bot.say("Added `{}` role to all server members! ({}/{})".format(role.name, count, member_count))
            else:
                await self.bot.say("Added `{}` role to all server members with the `{}` role! ({}/{})".format(role.name, frole.name, count, member_count))
        elif operation == "remove":
            if frole is None:
                await self.bot.say("Removed `{}` role from all server members! ({}/{})".format(role.name, count, member_count))
            else:
                await self.bot.say("Removed `{}` role from all server members with the `{}` role! ({}/{})".format(role.name, frole.name, count, member_count))

def setup(bot):
    bot.add_cog(GlobalRole(bot))