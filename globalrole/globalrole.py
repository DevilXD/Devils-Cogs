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
    async def globalrole(self, ctx, operation: str, *, role: str):
        """Add or remove a role from all users. Use 'add', 'remove' or 'stop' as operations."""
        if operation is None:
            await self.bot.send_cmd_help(ctx)
        valid_operations = ["add", "remove", "stop", "apply"]
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
            await self.bot.say("Operation already running - check the last message for progress!\nUse `[p]globalrole stop <role_name>` to stop the current operation.")
            return
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
        if operation == "apply":
            await self.bot.say("Please type in the role name that will be used to determine who will get the additional role applied:")
            msg = await self.bot.wait_for_message(timeout=60, author=author, channel=channel)
            if msg is None:
                await self.bot.say(":x: You took too long to enter the role name!")
            frole = discord.utils.get(server.roles, name=msg.content)
            if frole is None:
                await self.bot.say("That role doesn't seem to exist!")
                return
        count = 0
        member_count = len(server.members)
        mag = "Adding `{}` role to all server members... ({}/{})"
        mrg = "Removing `{}` role from all server members... ({}/{})"
        myg = "Applying `{}` role to all server members with `{}` role... ({}/{})"
        if operation == "add":
            desc = "You are about to add the `{}` role to all server members. Proceed?".format(role.name)
        elif operation == "remove":
            desc = "You are about to remove the `{}` role from all server members. Proceed?".format(role.name)
        elif operation == "apply":
            desc = "You are about to apply the `{}` role to all server members with the `{}` role. Proceed?".format(role.name, frole.name)
        e = discord.Embed(description=desc)
        confirm = await self.confirm_msg(ctx, e, 60)
        if confirm is False:
            return
        if operation == "add":
            msg = await self.bot.say(mag.format(role.name, count, member_count))
        elif operation == "remove":
            msg = await self.bot.say(mrg.format(role.name, count, member_count))
        elif operation == "apply":
            msg = await self.bot.say(myg.format(role.name, frole.name, count, member_count))
        self.busy = True
        for member in server.members:
            if operation == "add" and role not in member.roles:
                await self.bot.add_roles(member, role)
            elif operation == "remove" and role in member.roles:
                await self.bot.remove_roles(member, role)
            elif operation == "apply" and frole in member.roles and role not in member.roles:
                await self.bot.add_roles(member, role)
            count += 1
            if count % 10 == 0:
                try:
                    if operation == "add":
                        msg = await self.bot.edit_message(msg, new_content=mag.format(role.name, count, member_count))
                    elif operation == "remove":
                        msg = await self.bot.edit_message(msg, new_content=mrg.format(role.name, count, member_count))
                    elif operation == "apply":
                        msg = await self.bot.edit_message(msg, new_content=myg.format(role.name, frole.name, count, member_count))
                except:
                    if operation == "add":
                        msg = await self.bot.say(mag.format(role.name, count, member_count))
                    elif operation == "remove":
                        msg = await self.bot.say(mrg.format(role.name, count, member_count))
                    elif operation == "apply":
                        msg = await self.bot.say(myg.format(role.name, frole.name, count, member_count))
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
            await self.bot.say("Added `{}` role to all server members! ({}/{})".format(role.name, count, member_count))
        elif operation == "remove":
            await self.bot.say("Removed `{}` role from all server members! ({}/{})".format(role.name, count, member_count))
        elif operation == "apply":
            await self.bot.say("Applied `{}` role to all server members with the `{}` role! ({}/{})".format(role.name, frole.name, count, member_count))

def setup(bot):
    bot.add_cog(GlobalRole(bot))