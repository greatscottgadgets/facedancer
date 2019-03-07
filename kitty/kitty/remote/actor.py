# Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
#
# This file is part of Kitty.
#
# Kitty is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Kitty is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Kitty.  If not, see <http://www.gnu.org/licenses/>.

from kitty.remote import RpcServer
from kitty.remote import RpcClient
from kitty.data.report import Report


class RemoteActorServer(RpcServer):

    #
    # Since it is in the server, is should be called from the RPC like that
    # __meta__get_report
    #
    def get_report(self):
        report = self.impl.get_report()
        return report.to_dict()


class RemoteActor(RpcClient):

    def get_report(self):
        '''
        need to wrap get_report, since we need to parse the report
        '''
        report_dict = self._meta_get_report()
        report = Report.from_dict(report_dict)
        return report
