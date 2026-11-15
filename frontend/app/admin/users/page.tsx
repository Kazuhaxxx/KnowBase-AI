"use client";

import React, { useEffect, useState } from "react";
import type { AdminUserItem, UserRole } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";
import { api } from "@/services/api";
import { Badge, Button, Card } from "@/components/ui/primitives";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setUsers(await api.getAdminUsers());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users.");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleRoleChange = async (userId: string, role: UserRole) => {
    setError(null);
    try {
      const updated = await api.updateAdminUser(userId, { role });
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed.");
    }
  };

  const handleToggleActive = async (user: AdminUserItem) => {
    setError(null);
    try {
      const updated = await api.updateAdminUser(user.id, { is_active: !user.is_active });
      setUsers((prev) => prev.map((u) => (u.id === user.id ? updated : u)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed.");
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Users & Role-Based Access</h1>
        <p className="text-xs text-muted-foreground">
          Manage account status and assign role scopes (employee, it_staff, admin).
        </p>
      </div>

      {error && (
        <Card className="border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-400">
          {error}
        </Card>
      )}

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b bg-muted/40 text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-semibold">User</th>
                <th className="px-4 py-3 font-semibold">Department</th>
                <th className="px-4 py-3 font-semibold">Role</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Created</th>
                <th className="px-4 py-3 text-right font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="px-4 py-3">
                    <p className="font-semibold">{u.full_name}</p>
                    <p className="text-muted-foreground">{u.email}</p>
                  </td>
                  <td className="px-4 py-3">{u.department}</td>
                  <td className="px-4 py-3">
                    <select
                      value={u.role}
                      onChange={(e) => handleRoleChange(u.id, e.target.value as UserRole)}
                      className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                    >
                      <option value="employee">employee</option>
                      <option value="it_staff">it_staff</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={u.is_active ? "success" : "danger"}>
                      {u.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{formatDateTime(u.created_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      size="sm"
                      variant={u.is_active ? "outline" : "primary"}
                      onClick={() => handleToggleActive(u)}
                    >
                      {u.is_active ? "Deactivate" : "Activate"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

