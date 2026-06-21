<template>
  <div class="page-container">
    <n-card :title="t('users.title')">
      <template #header-extra>
        <n-button type="primary" @click="showCreateDialog = true">{{ t('users.createUser') }}</n-button>
      </template>

      <n-data-table
        :columns="columns"
        :data="users"
        :loading="loading"
        :pagination="{ pageSize: 10 }"
        striped
      />
    </n-card>

    <!-- 创建用户对话框 -->
    <n-modal v-model:show="showCreateDialog" :title="t('users.createUser')">
      <n-card style="width: 480px">
        <n-form label-placement="top">
          <n-form-item :label="t('users.username')">
            <n-input v-model:value="createForm.username" :placeholder="t('users.usernamePlaceholder')" />
          </n-form-item>
          <n-form-item :label="t('users.password')">
            <n-input v-model:value="createForm.password" type="password" :placeholder="t('users.passwordPlaceholder')" />
          </n-form-item>
          <n-form-item :label="t('users.role')">
            <n-select
              v-model:value="createForm.role"
              :options="roleOptions"
            />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="showCreateDialog = false">{{ t('common.cancel') }}</n-button>
            <n-button type="primary" :loading="submitting" @click="handleCreate">{{ t('common.confirm') }}</n-button>
          </n-space>
        </template>
      </n-card>
    </n-modal>

    <!-- 编辑用户对话框 -->
    <n-modal v-model:show="showEditDialog" :title="t('users.editUser')">
      <n-card style="width: 480px">
        <n-form label-placement="top">
          <n-form-item :label="t('users.role')">
            <n-select
              v-model:value="editForm.role"
              :options="roleOptions"
            />
          </n-form-item>
          <n-form-item :label="t('users.status')">
            <n-switch v-model:value="editForm.is_active" />
            <span style="margin-left: 8px">{{ editForm.is_active ? t('users.active') : t('users.disabled') }}</span>
          </n-form-item>
          <n-form-item :label="t('users.newPassword')">
            <n-input v-model:value="editForm.password" type="password" :placeholder="t('users.newPasswordPlaceholder')" />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="showEditDialog = false">{{ t('common.cancel') }}</n-button>
            <n-button type="primary" :loading="submitting" @click="handleUpdate">{{ t('common.confirm') }}</n-button>
          </n-space>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from "vue";
import { useDialog, useMessage } from "naive-ui";
import { useI18n } from "vue-i18n";
import { useAuthStore } from "../stores/auth";
import { api } from "../api/client";
import { useRouter } from "vue-router";

interface UserItem {
  id: string;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string | null;
}

const { t } = useI18n();
const dialog = useDialog();
const message = useMessage();
const auth = useAuthStore();
const router = useRouter();

const users = ref<UserItem[]>([]);
const loading = ref(false);
const submitting = ref(false);

const showCreateDialog = ref(false);
const showEditDialog = ref(false);

const createForm = ref({ username: "", password: "", role: "user" });
const editForm = ref({ id: "", role: "user", is_active: true, password: "" });

const roleOptions = [
  { label: "Admin", value: "admin" },
  { label: "User", value: "user" },
];

const columns = computed(() => [
  { title: t("users.username"), key: "username" },
  {
    title: t("users.role"),
    key: "role",
    render(row: UserItem) {
      return h("span", row.role === "admin" ? t("users.roleAdmin") : t("users.roleUser"));
    },
  },
  {
    title: t("users.status"),
    key: "is_active",
    render(row: UserItem) {
      return h(
        "span",
        { style: { color: row.is_active ? "var(--success)" : "var(--error)" } },
        row.is_active ? t("users.active") : t("users.disabled"),
      );
    },
  },
  {
    title: t("users.createdAt"),
    key: "created_at",
    render(row: UserItem) {
      return row.created_at ? new Date(row.created_at).toLocaleString() : "-";
    },
  },
  {
    title: t("common.actions"),
    key: "actions",
    render(row: UserItem) {
      return h("span", { style: { display: "flex", gap: "8px" } }, [
        h(
          "a",
          {
            style: { cursor: "pointer", color: "var(--primary)" },
            onClick: () => openEdit(row),
          },
          t("common.edit"),
        ),
        h(
          "a",
          {
            style: { cursor: "pointer", color: "var(--error)" },
            onClick: () => confirmDelete(row),
          },
          t("common.delete"),
        ),
      ]);
    },
  },
]);

async function fetchUsers() {
  loading.value = true;
  try {
    const res = await api.get<UserItem[]>("/auth/users");
    users.value = res.data;
  } catch (e: any) {
    if (e?.response?.status === 403 || e?.response?.status === 401) {
      message.error(t("users.noPermission"));
      router.push("/");
    } else {
      message.error(e?.response?.data?.detail || t("common.error"));
    }
  } finally {
    loading.value = false;
  }
}

async function handleCreate() {
  if (!createForm.value.username || !createForm.value.password) {
    message.warning(t("users.fillRequired"));
    return;
  }
  submitting.value = true;
  try {
    await api.post("/auth/users", createForm.value);
    message.success(t("users.createSuccess"));
    showCreateDialog.value = false;
    createForm.value = { username: "", password: "", role: "user" };
    await fetchUsers();
  } catch (e: any) {
    message.error(e?.response?.data?.detail || t("common.error"));
  } finally {
    submitting.value = false;
  }
}

function openEdit(user: UserItem) {
  editForm.value = { id: user.id, role: user.role, is_active: user.is_active, password: "" };
  showEditDialog.value = true;
}

async function handleUpdate() {
  submitting.value = true;
  try {
    const payload: Record<string, any> = { role: editForm.value.role, is_active: editForm.value.is_active };
    if (editForm.value.password) {
      payload.password = editForm.value.password;
    }
    await api.put(`/auth/users/${editForm.value.id}`, payload);
    message.success(t("users.updateSuccess"));
    showEditDialog.value = false;
    await fetchUsers();
  } catch (e: any) {
    message.error(e?.response?.data?.detail || t("common.error"));
  } finally {
    submitting.value = false;
  }
}

function confirmDelete(user: UserItem) {
  dialog.warning({
    title: t("users.deleteConfirm"),
    content: t("users.deleteConfirmMsg", { name: user.username }),
    positiveText: t("common.confirm"),
    negativeText: t("common.cancel"),
    onPositiveClick: async () => {
      try {
        await api.delete(`/auth/users/${user.id}`);
        message.success(t("users.deleteSuccess"));
        await fetchUsers();
      } catch (e: any) {
        message.error(e?.response?.data?.detail || t("common.error"));
      }
    },
  });
}

onMounted(() => {
  fetchUsers();
});
</script>