import discord
import asyncio
from discord.ext import commands
from cogs.utils import checks

class GlobalRole:

    def __init__(self, bot):
        self.bot = bot
        self.stop = False
        self.busy = False

    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def globalrole(self, ctx, operation: str, *, role: str):
        """Add or remove a role from all users. Use 'add', 'remove' or 'stop' as operations."""
        if operation is None:
            await self.bot.send_cmd_help(ctx)
        valid_operations = ["add", "remove", "stop"]
        server = ctx.message.server
        author = ctx.message.author
        if operation == "stop":
            self.stop = self.busy
            if self.stop == True:
                await self.bot.say("Stopping...")
            else:
                await self.bot.say("There are no operations running right now!")
            return
        if self.busy == True:
            await self.bot.say("Already running - check the previous message for progress!")
            return
        operation = operation.lower()
        if operation not in valid_operations:
            await self.bot.say("Invalid operation!")
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
        self.busy = True
        count = 0
        member_count = len(server.members)
        mag = "Adding `{}` role to all server members... ({}/{})"
        mrg = "Removing `{}` role from all server members... ({}/{})"
        if operation == "add":
            msg = await self.bot.say(mag.format(role.name, count, member_count))
        elif operation == "remove":
            msg = await self.bot.say(mrg.format(role.name, count, member_count))
        for member in server.members:
            if operation == "add" and role not in member.roles:
                await self.bot.add_roles(member, role)
            elif operation == "remove" and role in member.roles:
                await self.bot.remove_roles(member, role)
            count += 1
            if count % 10 == 0:
                try:
                    if operation == "add":
                        msg = await self.bot.edit_message(msg, new_content=mag.format(role.name, count, member_count))
                    elif operation == "remove":
                        msg = await self.bot.edit_message(msg, new_content=mrg.format(role.name, count, member_count))
                except:
                    if operation == "add":
                        msg = await self.bot.say(mag.format(role.name, count, member_count))
                    elif operation == "remove":
                        msg = await self.bot.say(mrg.format(role.name, count, member_count))
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

def setup(bot):
    bot.add_cog(GlobalRole(bot))