# -*-coding:utf-8-*-
import logging
import mimetypes

import requests

import aiohttp
from rocketchat_API.APIExceptions.RocketExceptions import (
    RocketAuthenticationException,
    RocketConnectionException,
    RocketMissingParamException,
)

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


class RocketChat:
    API_path = '/api/v1/'

    def __init__(self, user=None, password=None, auth_token=None, user_id=None,
                 server_url='http://127.0.0.1:3000', ssl_verify=True, proxies=None,
                 timeout=30):
        """Creates a RocketChat object and does login on the specified server"""
        self.server_url = server_url
        self.proxies = proxies
        self.ssl_verify = ssl_verify
        self.timeout = timeout
        self.session = aiohttp.ClientSession()
        self.headers = {}
        if user and password:
            self.login(user, password)
        if auth_token and user_id:
            self.headers['X-Auth-Token'] = auth_token
            self.headers['X-User-Id'] = user_id

    @staticmethod
    def __reduce_kwargs(kwargs):
        if 'kwargs' in kwargs:
            for arg in kwargs['kwargs'].keys():
                kwargs[arg] = kwargs['kwargs'][arg]

            del kwargs['kwargs']
        return kwargs

    async def __call_api_get(self, method, **kwargs):
        args = self.__reduce_kwargs(kwargs)
        async with self.session.get(self.server_url + self.API_path + method + '?' +
                        '&'.join([i + '=' + str(args[i])
                                  for i in args.keys()]),
                        headers=self.headers,
                        ssl=self.ssl_verify,
                        #proxies=self.proxies,
                        timeout=self.timeout
                        ) as resp:
            return await resp.json()

    async def __call_api_post(self, method, files=None, use_json=True, **kwargs):
        reduced_args = self.__reduce_kwargs(kwargs)
        # Since pass is a reserved word in Python it has to be injected on the request dict
        # Some methods use pass (users.register) and others password (users.create)
        if 'password' in reduced_args and method != 'users.create':
            reduced_args['pass'] = reduced_args['password']

        form_data = None
        if files:
            use_json = False
            form_data = aiohttp.FormData()
            for file_key, file in files.items():
                form_data.add_field(file_key, file[1],
                                    content_type=file[2],
                                    filename=file[0])
            for key, value in reduced_args.items():
                form_data.add_field(key, value)

        if use_json and not form_data:
            async with self.session.post(self.server_url + self.API_path + method,
                             json=reduced_args,
                             headers=self.headers,
                             ssl=self.ssl_verify,
                             #proxies=self.proxies,
                             timeout=self.timeout
                             ) as resp:
                return await resp.json()
        else:
            async with self.session.post(self.server_url + self.API_path + method,
                             data=form_data,
                             headers=self.headers,
                             ssl=self.ssl_verify,
                             #proxies=self.proxies,
                             timeout=self.timeout
                             ) as resp:
                return await resp.json()

    # Authentication

    def login(self, user, password):
        login_request = requests.post(self.server_url + self.API_path + 'login',
                                      data={'username': user,
                                            'password': password},
                                      verify=self.ssl_verify,
                                      proxies=self.proxies)
        if login_request.status_code == 401:
            print('login_request', login_request.text)
            raise RocketAuthenticationException()

        if login_request.status_code == 200:
            if login_request.json().get('status') == "success":
                self.headers['X-Auth-Token'] = login_request.json().get('data').get('authToken')
                self.headers['X-User-Id'] = login_request.json().get('data').get('userId')
                return login_request
            else:
                raise RocketAuthenticationException()
        else:
            raise RocketConnectionException()

    async def me(self, **kwargs):
        """	Displays information about the authenticated user."""
        return await self.__call_api_get('me', kwargs=kwargs)

    async def logout(self, **kwargs):
        """Invalidate your REST rocketchat_API authentication token."""
        return await self.__call_api_post('logout', kwargs=kwargs)

    # Miscellaneous information

    async def info(self, **kwargs):
        """Information about the Rocket.Chat server."""
        return await self.__call_api_get('info', kwargs=kwargs)

    async def directory(self, query, **kwargs):
        """Search by users or channels on all server."""
        if isinstance(query, dict):
            query = str(query).replace("'", '"')

        return await self.__call_api_get('directory', query=query, kwargs=kwargs)

    async def spotlight(self, query, **kwargs):
        """Searches for users or rooms that are visible to the user."""
        return await self.__call_api_get('spotlight', query=query, kwargs=kwargs)

    async def users_get_preferences(self, **kwargs):
        """Gets all preferences of user."""
        return await self.__call_api_get('users.getPreferences', kwargs=kwargs)

    async def users_set_preferences(self, user_id, data, **kwargs):
        """Set user’s preferences."""
        return await self.__call_api_post('users.setPreferences', userId=user_id, data=data, kwargs=kwargs)

    # Users

    async def users_info(self, user_id=None, username=None, **kwargs):
        """Gets a user’s information, limited to the caller’s permissions."""
        if user_id:
            return await self.__call_api_get('users.info', userId=user_id, kwargs=kwargs)
        elif username:
            return await self.__call_api_get('users.info', username=username, kwargs=kwargs)
        else:
            raise RocketMissingParamException('userID or username required')

    async def users_list(self, **kwargs):
        """All of the users and their information, limited to permissions."""
        return await self.__call_api_get('users.list', kwargs=kwargs)

    async def users_get_presence(self, user_id=None, username=None, **kwargs):
        """Gets the online presence of the a user."""
        if user_id:
            return await self.__call_api_get('users.getPresence', userId=user_id, kwargs=kwargs)
        elif username:
            return await self.__call_api_get('users.getPresence', username=username, kwargs=kwargs)
        else:
            raise RocketMissingParamException('userID or username required')

    async def users_create(self, email, name, password, username, **kwargs):
        """Creates a user"""
        return await self.__call_api_post('users.create', email=email, name=name, password=password, username=username,
                                    kwargs=kwargs)

    async def users_delete(self, user_id, **kwargs):
        """Deletes a user"""
        return await self.__call_api_post('users.delete', userId=user_id, **kwargs)

    async def users_register(self, email, name, password, username, **kwargs):
        """Register a new user."""
        return await self.__call_api_post('users.register', email=email, name=name, password=password, username=username,
                                    kwargs=kwargs)

    async def users_get_avatar(self, user_id=None, username=None, **kwargs):
        """Gets the URL for a user’s avatar."""
        if user_id:
            return await self.__call_api_get('users.getAvatar', userId=user_id, kwargs=kwargs)
        elif username:
            return await self.__call_api_get('users.getAvatar', username=username, kwargs=kwargs)
        else:
            raise RocketMissingParamException('userID or username required')

    async def users_set_avatar(self, avatar_url, **kwargs):
        """Set a user’s avatar"""
        if avatar_url.startswith('http://') or avatar_url.startswith('https://'):
            return await self.__call_api_post('users.setAvatar', avatarUrl=avatar_url, kwargs=kwargs)
        else:
            avatar_file = {"image": open(avatar_url, "rb")}
            return await self.__call_api_post('users.setAvatar', files=avatar_file, kwargs=kwargs)

    async def users_reset_avatar(self, user_id=None, username=None, **kwargs):
        """Reset a user’s avatar"""
        if user_id:
            return await self.__call_api_post('users.resetAvatar', userId=user_id, kwargs=kwargs)
        elif username:
            return await self.__call_api_post('users.resetAvatar', username=username, kwargs=kwargs)
        else:
            raise RocketMissingParamException('userID or username required')

    async def users_create_token(self, user_id=None, username=None, **kwargs):
        """Create a user authentication token."""
        if user_id:
            return await self.__call_api_post('users.createToken', userId=user_id, kwargs=kwargs)
        elif username:
            return await self.__call_api_post('users.createToken', username=username, kwargs=kwargs)
        else:
            raise RocketMissingParamException('userID or username required')

    async def users_update(self, user_id, **kwargs):
        """Update an existing user."""
        return await self.__call_api_post('users.update', userId=user_id, data=kwargs)

    async def users_forgot_password(self, email, **kwargs):
        """Send email to reset your password."""
        return await self.__call_api_post('users.forgotPassword', email=email, data=kwargs)

    # Chat

    async def chat_post_message(self, text, room_id=None, channel=None, **kwargs):
        """Posts a new chat message."""
        if room_id:
            return await self.__call_api_post('chat.postMessage', roomId=room_id, text=text, kwargs=kwargs)
        elif channel:
            return await self.__call_api_post('chat.postMessage', channel=channel, text=text, kwargs=kwargs)
        else:
            raise RocketMissingParamException('roomId or channel required')

    async def chat_get_message(self, msg_id, **kwargs):
        return await self.__call_api_get('chat.getMessage', msgId=msg_id, kwargs=kwargs)

    async def chat_pin_message(self, msg_id, **kwargs):
        return await self.__call_api_post('chat.pinMessage', messageId=msg_id, kwargs=kwargs)

    async def chat_unpin_message(self, msg_id, **kwargs):
        return await self.__call_api_post('chat.unPinMessage', messageId=msg_id, kwargs=kwargs)

    async def chat_star_message(self, msg_id, **kwargs):
        return await self.__call_api_post('chat.starMessage', messageId=msg_id, kwargs=kwargs)

    async def chat_unstar_message(self, msg_id, **kwargs):
        return await self.__call_api_post('chat.unStarMessage', messageId=msg_id, kwargs=kwargs)

    async def chat_delete(self, room_id, msg_id, **kwargs):
        """Deletes a chat message."""
        return await self.__call_api_post('chat.delete', roomId=room_id, msgId=msg_id, kwargs=kwargs)

    async def chat_update(self, room_id, msg_id, text, **kwargs):
        """Updates the text of the chat message."""
        return await self.__call_api_post('chat.update', roomId=room_id, msgId=msg_id, text=text, kwargs=kwargs)

    async def chat_react(self, msg_id, emoji='smile', **kwargs):
        """Updates the text of the chat message."""
        return await self.__call_api_post('chat.react', messageId=msg_id, emoji=emoji, kwargs=kwargs)

    async def chat_search(self, room_id, search_text, **kwargs):
        """Search for messages in a channel by id and text message."""
        return await self.__call_api_get('chat.search', roomId=room_id, searchText=search_text, kwargs=kwargs)

    async def chat_get_message_read_receipts(self, message_id, **kwargs):
        """Get Message Read Receipts"""
        return await self.__call_api_get('chat.getMessageReadReceipts', messageId=message_id, kwargs=kwargs)

    # Channels

    async def channels_list(self, **kwargs):
        """Retrieves all of the channels from the server."""
        return await self.__call_api_get('channels.list', kwargs=kwargs)

    async def channels_list_joined(self, **kwargs):
        """Lists all of the channels the calling user has joined"""
        return await self.__call_api_get('channels.list.joined', kwargs=kwargs)

    async def channels_info(self, room_id=None, channel=None, **kwargs):
        """Gets a channel’s information."""
        if room_id:
            return await self.__call_api_get('channels.info', roomId=room_id, kwargs=kwargs)
        elif channel:
            return await self.__call_api_get('channels.info', roomName=channel, kwargs=kwargs)
        else:
            raise RocketMissingParamException('roomId or channel required')

    async def channels_history(self, room_id, **kwargs):
        """Retrieves the messages from a channel."""
        return await self.__call_api_get('channels.history', roomId=room_id, kwargs=kwargs)

    async def channels_add_all(self, room_id, **kwargs):
        """Adds all of the users of the Rocket.Chat server to the channel."""
        return await self.__call_api_post('channels.addAll', roomId=room_id, kwargs=kwargs)

    async def channels_add_moderator(self, room_id, user_id, **kwargs):
        """Gives the role of moderator for a user in the current channel."""
        return await self.__call_api_post('channels.addModerator', roomId=room_id, userId=user_id, kwargs=kwargs)

    async def channels_remove_moderator(self, room_id, user_id, **kwargs):
        """Removes the role of moderator from a user in the current channel."""
        return await self.__call_api_post('channels.removeModerator', roomId=room_id, userId=user_id, kwargs=kwargs)

    async def channels_add_owner(self, room_id, user_id=None, username=None, **kwargs):
        """Gives the role of owner for a user in the current channel."""
        if user_id:
            return await self.__call_api_post('channels.addOwner', roomId=room_id, userId=user_id, kwargs=kwargs)
        elif username:
            return await self.__call_api_post('channels.addOwner', roomId=room_id, username=username, kwargs=kwargs)
        else:
            raise RocketMissingParamException('userID or username required')

    async def channels_remove_owner(self, room_id, user_id, **kwargs):
        """Removes the role of owner from a user in the current channel."""
        return await self.__call_api_post('channels.removeOwner', roomId=room_id, userId=user_id, kwargs=kwargs)

    async def channels_archive(self, room_id, **kwargs):
        """Archives a channel."""
        return await self.__call_api_post('channels.archive', roomId=room_id, kwargs=kwargs)

    async def channels_unarchive(self, room_id, **kwargs):
        """Unarchives a channel."""
        return await self.__call_api_post('channels.unarchive', roomId=room_id, kwargs=kwargs)

    async def channels_close(self, room_id, **kwargs):
        """Removes the channel from the user’s list of channels."""
        return await self.__call_api_post('channels.close', roomId=room_id, kwargs=kwargs)

    async def channels_open(self, room_id, **kwargs):
        """Adds the channel back to the user’s list of channels."""
        return await self.__call_api_post('channels.open', roomId=room_id, kwargs=kwargs)

    async def channels_create(self, name, **kwargs):
        """Creates a new public channel, optionally including users."""
        return await self.__call_api_post('channels.create', name=name, kwargs=kwargs)

    async def channels_get_integrations(self, room_id, **kwargs):
        """Retrieves the integrations which the channel has"""
        return await self.__call_api_get('channels.getIntegrations', roomId=room_id, kwargs=kwargs)

    async def channels_invite(self, room_id, user_id, **kwargs):
        """Adds a user to the channel."""
        return await self.__call_api_post('channels.invite', roomId=room_id, userId=user_id, kwargs=kwargs)

    async def channels_kick(self, room_id, user_id, **kwargs):
        """Removes a user from the channel."""
        return await self.__call_api_post('channels.kick', roomId=room_id, userId=user_id, kwargs=kwargs)

    async def channels_leave(self, room_id, **kwargs):
        """Causes the callee to be removed from the channel."""
        return await self.__call_api_post('channels.leave', roomId=room_id, kwargs=kwargs)

    async def channels_rename(self, room_id, name, **kwargs):
        """Changes the name of the channel."""
        return await self.__call_api_post('channels.rename', roomId=room_id, name=name, kwargs=kwargs)

    async def channels_set_description(self, room_id, description, **kwargs):
        """Sets the description for the channel."""
        return await self.__call_api_post('channels.setDescription', roomId=room_id, description=description, kwargs=kwargs)

    async def channels_set_join_code(self, room_id, join_code, **kwargs):
        """Sets the code required to join the channel."""
        return await self.__call_api_post('channels.setJoinCode', roomId=room_id, joinCode=join_code, kwargs=kwargs)

    async def channels_set_read_only(self, room_id, read_only, **kwargs):
        """Sets whether the channel is read only or not."""
        return await self.__call_api_post('channels.setReadOnly', roomId=room_id, readOnly=bool(read_only), kwargs=kwargs)

    async def channels_set_topic(self, room_id, topic, **kwargs):
        """Sets the topic for the channel."""
        return await self.__call_api_post('channels.setTopic', roomId=room_id, topic=topic, kwargs=kwargs)

    async def channels_set_type(self, room_id, a_type, **kwargs):
        """Sets the type of room this channel should be. The type of room this channel should be, either c or p."""
        return await self.__call_api_post('channels.setType', roomId=room_id, type=a_type, kwargs=kwargs)

    async def channels_set_announcement(self, room_id, announce, **kwargs):
        """Sets the announcement for the channel."""
        return await self.__call_api_post('channels.setAnnouncement', roomId=room_id, announcement=announce, kwargs=kwargs)

    async def channels_set_custom_fields(self, rid, custom_fields):
        """Sets the custom fields for the channel."""
        return await self.__call_api_post('channels.setCustomFields', roomId=rid, customFields=custom_fields)

    async def channels_delete(self, room_id=None, channel=None, **kwargs):
        """Delete a public channel."""
        if room_id:
            return await self.__call_api_post('channels.delete', roomId=room_id, kwargs=kwargs)
        elif channel:
            return await self.__call_api_post('channels.delete', roomName=channel, kwargs=kwargs)
        else:
            raise RocketMissingParamException('roomId or channel required')

    async def channels_members(self, room_id=None, channel=None, **kwargs):
        """Lists all channel users."""
        if room_id:
            return await self.__call_api_get('channels.members', roomId=room_id, kwargs=kwargs)
        elif channel:
            return await self.__call_api_get('channels.members', roomName=channel, kwargs=kwargs)
        else:
            raise RocketMissingParamException('roomId or channel required')

    async def channels_roles(self, room_id=None, room_name=None, **kwargs):
        """Lists all user’s roles in the channel."""
        if room_id:
            return await self.__call_api_get('channels.roles', roomId=room_id, kwargs=kwargs)
        elif room_name:
            return await self.__call_api_get('channels.roles', roomName=room_name, kwargs=kwargs)
        else:
            raise RocketMissingParamException('roomId or room_name required')

    async def channels_files(self, room_id=None, room_name=None, **kwargs):
        """Retrieves the files from a channel."""
        if room_id:
            return await self.__call_api_get('channels.files', roomId=room_id, kwargs=kwargs)
        elif room_name:
            return await self.__call_api_get('channels.files', roomName=room_name, kwargs=kwargs)
        else:
            raise RocketMissingParamException('roomId or room_name required')

    async def channels_get_all_user_mentions_by_channel(self, room_id, **kwargs):
        """Gets all the mentions of a channel."""
        return await self.__call_api_get('channels.getAllUserMentionsByChannel', roomId=room_id, kwargs=kwargs)

    # Groups

    async def groups_list_all(self, **kwargs):
        """
        List all the private groups on the server.
        The calling user must have the 'view-room-administration' right
        """
        return await self.__call_api_get('groups.listAll', kwargs=kwargs)

    async def groups_list(self, **kwargs):
        """List the private groups the caller is part of."""
        return await self.__call_api_get('groups.list', kwargs=kwargs)

    async def groups_history(self, room_id, **kwargs):
        """Retrieves the messages from a private group."""
        return await self.__call_api_get('groups.history', roomId=room_id, kwargs=kwargs)

    async def groups_add_moderator(self, room_id, user_id, **kwargs):
        """Gives the role of moderator for a user in the current groups."""
        return await self.__call_api_post('groups.addModerator', roomId=room_id, userId=user_id, kwargs=kwargs)

    async def groups_remove_moderator(self, room_id, user_id, **kwargs):
        """Removes the role of moderator from a user in the current groups."""
        return await self.__call_api_post('groups.removeModerator', roomId=room_id, userId=user_id, kwargs=kwargs)

    async def groups_add_owner(self, room_id, user_id, **kwargs):
        """Gives the role of owner for a user in the current Group."""
        return await self.__call_api_post('groups.addOwner', roomId=room_id, userId=user_id, kwargs=kwargs)

    async def groups_remove_owner(self, room_id, user_id, **kwargs):
        """Removes the role of owner from a user in the current Group."""
        return await self.__call_api_post('groups.removeOwner', roomId=room_id, userId=user_id, kwargs=kwargs)

    async def groups_archive(self, room_id, **kwargs):
        """Archives a private group, only if you’re part of the group."""
        return await self.__call_api_post('groups.archive', roomId=room_id, kwargs=kwargs)

    async def groups_unarchive(self, room_id, **kwargs):
        """Unarchives a private group."""
        return await self.__call_api_post('groups.unarchive', roomId=room_id, kwargs=kwargs)

    async def groups_close(self, room_id, **kwargs):
        """Removes the private group from the user’s list of groups, only if you’re part of the group."""
        return await self.__call_api_post('groups.close', roomId=room_id, kwargs=kwargs)

    async def groups_create(self, name, **kwargs):
        """Creates a new private group, optionally including users, only if you’re part of the group."""
        return await self.__call_api_post('groups.create', name=name, kwargs=kwargs)

    async def groups_get_integrations(self, room_id, **kwargs):
        """Retrieves the integrations which the group has"""
        return await self.__call_api_get('groups.getIntegrations', roomId=room_id, kwargs=kwargs)

    async def groups_info(self, room_id=None, room_name=None, **kwargs):
        """GRetrieves the information about the private group, only if you’re part of the group."""
        if room_id:
            return await self.__call_api_get('groups.info', roomId=room_id, kwargs=kwargs)
        elif room_name:
            return await self.__call_api_get('groups.info', roomName=room_name, kwargs=kwargs)
        else:
            raise RocketMissingParamException('roomId or roomName required')

    async def groups_invite(self, room_id, user_id, **kwargs):
        """Adds a user to the private group."""
        return await self.__call_api_post('groups.invite', roomId=room_id, userId=user_id, kwargs=kwargs)

    async def groups_kick(self, room_id, user_id, **kwargs):
        """Removes a user from the private group."""
        return await self.__call_api_post('groups.kick', roomId=room_id, userId=user_id, kwargs=kwargs)

    async def groups_leave(self, room_id, **kwargs):
        """Causes the callee to be removed from the private group, if they’re part of it and are not the last owner."""
        return await self.__call_api_post('groups.leave', roomId=room_id, kwargs=kwargs)

    async def groups_open(self, room_id, **kwargs):
        """Adds the private group back to the user’s list of private groups."""
        return await self.__call_api_post('groups.open', roomId=room_id, kwargs=kwargs)

    async def groups_rename(self, room_id, name, **kwargs):
        """Changes the name of the private group."""
        return await self.__call_api_post('groups.rename', roomId=room_id, name=name, kwargs=kwargs)

    async def groups_set_description(self, room_id, description, **kwargs):
        """Sets the description for the private group."""
        return await self.__call_api_post('groups.setDescription', roomId=room_id, description=description, kwargs=kwargs)

    async def groups_set_read_only(self, room_id, read_only, **kwargs):
        """Sets whether the group is read only or not."""
        return await self.__call_api_post('groups.setReadOnly', roomId=room_id, readOnly=bool(read_only), kwargs=kwargs)

    async def groups_set_topic(self, room_id, topic, **kwargs):
        """Sets the topic for the private group."""
        return await self.__call_api_post('groups.setTopic', roomId=room_id, topic=topic, kwargs=kwargs)

    async def groups_set_type(self, room_id, a_type, **kwargs):
        """Sets the type of room this group should be. The type of room this channel should be, either c or p."""
        return await self.__call_api_post('groups.setType', roomId=room_id, type=a_type, kwargs=kwargs)

    async def groups_delete(self, room_id=None, group=None, **kwargs):
        """Delete a private group."""
        if room_id:
            return await self.__call_api_post('groups.delete', roomId=room_id, kwargs=kwargs)
        elif group:
            return await self.__call_api_post('groups.delete', roomName=group, kwargs=kwargs)
        else:
            raise RocketMissingParamException('roomId or group required')

    async def groups_members(self, room_id=None, group=None, **kwargs):
        """Lists all group users."""
        if room_id:
            return await self.__call_api_get('groups.members', roomId=room_id, kwargs=kwargs)
        elif group:
            return await self.__call_api_get('groups.members', roomName=group, kwargs=kwargs)
        else:
            raise RocketMissingParamException('roomId or group required')

    async def groups_roles(self, room_id=None, room_name=None, **kwargs):
        """Lists all user’s roles in the private group."""
        if room_id:
            return await self.__call_api_get('groups.roles', roomId=room_id, kwargs=kwargs)
        elif room_name:
            return await self.__call_api_get('groups.roles', roomName=room_name, kwargs=kwargs)
        else:
            raise RocketMissingParamException('roomId or room_name required')

    async def groups_files(self, room_id=None, room_name=None, **kwargs):
        """Retrieves the files from a private group."""
        if room_id:
            return await self.__call_api_get('groups.files', roomId=room_id, kwargs=kwargs)
        elif room_name:
            return await self.__call_api_get('groups.files', roomName=room_name, kwargs=kwargs)
        else:
            raise RocketMissingParamException('roomId or room_name required')

    # IM
    async def im_list(self, **kwargs):
        """List the private im chats for logged user"""
        return await self.__call_api_get('im.list', kwargs=kwargs)

    async def im_list_everyone(self, **kwargs):
        """List all direct message the caller in the server."""
        return await self.__call_api_get('im.list.everyone', kwargs=kwargs)

    async def im_history(self, room_id, **kwargs):
        """Retrieves the history for a private im chat"""
        return await self.__call_api_get('im.history', roomId=room_id, kwargs=kwargs)

    async def im_create(self, username, **kwargs):
        """Create a direct message session with another user."""
        return await self.__call_api_post('im.create', username=username, kwargs=kwargs)

    async def im_open(self, room_id, **kwargs):
        """Adds the direct message back to the user’s list of direct messages."""
        return await self.__call_api_post('im.open', roomId=room_id, kwargs=kwargs)

    async def im_close(self, room_id, **kwargs):
        """Removes the direct message from the user’s list of direct messages."""
        return await self.__call_api_post('im.close', roomId=room_id, kwargs=kwargs)

    async def im_messages_others(self, room_id, **kwargs):
        """Retrieves the messages from any direct message in the server"""
        return await self.__call_api_get('im.messages.others', roomId=room_id, kwargs=kwargs)

    async def im_set_topic(self, room_id, topic, **kwargs):
        """Sets the topic for the direct message"""
        return await self.__call_api_post('im.setTopic', roomId=room_id, topic=topic, kwargs=kwargs)

    async def im_files(self, room_id=None, user_name=None, **kwargs):
        """Retrieves the files from a direct message."""
        if room_id:
            return await self.__call_api_get('im.files', roomId=room_id, kwargs=kwargs)
        elif user_name:
            return await self.__call_api_get('im.files', username=user_name, kwargs=kwargs)
        else:
            raise RocketMissingParamException('roomId or username required')

    async def im_counters(self, room_id=None, user_name=None, **kwargs):
        """Gets counters of direct messages."""
        if room_id:
            return await self.__call_api_get('im.counters', roomId=room_id, kwargs=kwargs)
        elif user_name:
            return await self.__call_api_get('im.counters', username=user_name, kwargs=kwargs)
        else:
            raise RocketMissingParamException('roomId or username required')

    # Statistics

    async def statistics(self, **kwargs):
        """Retrieves the current statistics"""
        return await self.__call_api_get('statistics', kwargs=kwargs)

    async def statistics_list(self, **kwargs):
        """Selectable statistics about the Rocket.Chat server."""
        return await self.__call_api_get('statistics.list', kwargs=kwargs)

    # Settings

    async def settings_get(self, _id):
        """Gets the setting for the provided _id."""
        return await self.__call_api_get('settings/' + _id)

    async def settings_update(self, _id, value):
        """Updates the setting for the provided _id."""
        return await self.__call_api_post('settings/' + _id, value=value)

    async def settings(self):
        """List all private settings."""
        return await self.__call_api_get('settings')

    # Rooms

    async def rooms_upload(self, rid, file, **kwargs):
        """Post a message with attached file to a dedicated room."""
        files = {
            'file': (file, open(file, 'rb'), 'image/png', {})
        }
        return await self.__call_api_post('rooms.upload/' + rid, kwargs=kwargs, use_json=False, files=files)

    async def rooms_get(self, **kwargs):
        """Get all opened rooms for this user."""
        return await self.__call_api_get('rooms.get', kwargs=kwargs)

    async def rooms_clean_history(self, room_id, latest, oldest, **kwargs):
        """Cleans up a room, removing messages from the provided time range."""
        return await self.__call_api_post('rooms.cleanHistory', roomId=room_id, latest=latest, oldest=oldest, kwargs=kwargs)

    async def rooms_favorite(self, room_id=None, room_name=None, favorite=True):
        """Favorite or unfavorite room."""
        if room_id is not None:
            return await self.__call_api_post('rooms.favorite', roomId=room_id, favorite=favorite)
        elif room_name is not None:
            return await self.__call_api_post('rooms.favorite', roomName=room_name, favorite=favorite)
        else:
            raise RocketMissingParamException('roomId or roomName required')

    async def rooms_info(self, room_id=None, room_name=None):
        """Retrieves the information about the room."""
        if room_id is not None:
            return await self.__call_api_get('rooms.info', roomId=room_id)
        elif room_name is not None:
            return await self.__call_api_get('rooms.info', roomName=room_name)
        else:
            raise RocketMissingParamException('roomId or roomName required')

    # Subscriptions

    async def subscriptions_get(self, **kwargs):
        """Get all subscriptions."""
        return await self.__call_api_get('subscriptions.get', kwargs=kwargs)

    async def subscriptions_get_one(self, room_id, **kwargs):
        """Get the subscription by room id."""
        return await self.__call_api_get('subscriptions.getOne', roomId=room_id, kwargs=kwargs)

    async def subscriptions_unread(self, room_id, **kwargs):
        """Mark messages as unread by roomId or from a message"""
        return await self.__call_api_post('subscriptions.unread', roomId=room_id, kwargs=kwargs)

    # Assets

    async def assets_set_asset(self, asset_name, file, **kwargs):
        """Set an asset image by name."""
        content_type = mimetypes.MimeTypes().guess_type(file)
        files = {
            asset_name: (file, open(file, 'rb'), content_type[0], {'Expires': '0'}),
        }
        return await self.__call_api_post('assets.setAsset', kwargs=kwargs, use_json=False, files=files)

    async def assets_unset_asset(self, asset_name):
        """Unset an asset by name"""
        return await self.__call_api_post('assets.unsetAsset', assetName=asset_name)
