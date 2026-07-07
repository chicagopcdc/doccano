<template>
  <v-card>
    <!-- Header actions only for project admins -->
    <v-card-title v-if="isProjectAdmin">
      <!-- Top action menu for import/export and assignment ops -->
      <action-menu
        @upload="$router.push('dataset/import')"
        @download="$router.push('dataset/export')"
        @assign="dialogAssignment = true"
        @reset="dialogReset = true"
      />

      <!-- Bulk delete (selected rows) -->
      <v-btn
        class="text-capitalize ms-2"
        :disabled="!canDelete"
        outlined
        @click.stop="dialogDelete = true"
      >
        {{ $t('generic.delete') }}
      </v-btn>

      <v-spacer />

      <!-- Delete ALL examples in the project -->
      <v-btn
        :disabled="!item.count"
        class="text-capitalize"
        color="error"
        @click="dialogDeleteAll = true"
      >
        {{ $t('generic.deleteAll') }}
      </v-btn>

      <!-- Confirmation dialogs -->
      <v-dialog v-model="dialogDelete">
        <form-delete
          :selected="selected"
          :item-key="itemKey"
          @cancel="dialogDelete = false"
          @remove="remove"
        />
      </v-dialog>

      <v-dialog v-model="dialogDeleteAll">
        <form-delete-bulk @cancel="dialogDeleteAll = false" @remove="removeAll" />
      </v-dialog>

      <v-dialog v-model="dialogAssignment">
        <form-assignment @assigned="assigned" @cancel="dialogAssignment = false" />
      </v-dialog>

      <v-dialog v-model="dialogReset">
        <form-reset-assignment @cancel="dialogReset = false" @reset="resetAssignment" />
      </v-dialog>
    </v-card-title>

    <!-- Render list type based on project kind -->
    <image-list
      v-if="project.isImageProject"
      v-model="selected"
      :items="item.items"
      :is-admin="user.isProjectAdmin"
      :is-loading="isLoading"
      :members="members"
      :total="item.count"
      @update:query="updateQuery"
      @click:labeling="movePage"
      @assign="assign"
      @unassign="unassign"
    />
    <audio-list
      v-else-if="project.isAudioProject"
      v-model="selected"
      :items="item.items"
      :is-admin="user.isProjectAdmin"
      :is-loading="isLoading"
      :members="members"
      :total="item.count"
      @update:query="updateQuery"
      @click:labeling="movePage"
      @assign="assign"
      @unassign="unassign"
    />
    <document-list
      v-else
      v-model="selected"
      :items="item.items"
      :is-admin="user.isProjectAdmin"
      :is-loading="isLoading"
      :members="members"
      :total="item.count"
      @update:query="updateQuery"
      @click:labeling="movePage"
      @edit="editItem"
      @assign="assign"
      @unassign="unassign"
    />
  </v-card>
</template>

<script lang="ts">
import _ from 'lodash'
import { mapGetters } from 'vuex'
import Vue from 'vue'
import { NuxtAppOptions } from '@nuxt/types'
import DocumentList from '@/components/example/DocumentList.vue'
import FormAssignment from '~/components/example/FormAssignment.vue'
import FormDelete from '@/components/example/FormDelete.vue'
import FormDeleteBulk from '@/components/example/FormDeleteBulk.vue'
import FormResetAssignment from '~/components/example/FormResetAssignment.vue'
import ActionMenu from '~/components/example/ActionMenu.vue'
import AudioList from '~/components/example/AudioList.vue'
import ImageList from '~/components/example/ImageList.vue'
import { getLinkToAnnotationPage } from '~/presenter/linkToAnnotationPage'
import { ExampleDTO, ExampleListDTO } from '~/services/application/example/exampleData'
import { MemberItem } from '~/domain/models/member/member'

export default Vue.extend({
  components: {
    ActionMenu,
    AudioList,
    DocumentList,
    ImageList,
    FormAssignment,
    FormDelete,
    FormDeleteBulk,
    FormResetAssignment
  },

  // Use the project layout (sidebar/breadcrumbs, etc.)
  layout: 'project',

  // Must be authenticated and have the current project loaded
  middleware: ['check-auth', 'auth', 'setCurrentProject'],

  /**
   * Route validation:
   * - params.id must be digits
   * - query.limit and query.offset (if present) must be digits
   *   (empty string allowed because Nuxt may pass it that way)
   */
  validate({ params, query }: NuxtAppOptions) {
    return /^\d+$/.test(params.id) && /^\d+|$/.test(query.limit) && /^\d+|$/.test(query.offset)
  },

  data() {
    return {
      dialogDelete: false, // confirm delete selected
      dialogDeleteAll: false, // confirm delete all
      dialogAssignment: false, // open assignment dialog
      dialogReset: false, // open reset assignment dialog
      item: {} as ExampleListDTO, // server response: { items, count, ... }
      selected: [] as ExampleDTO[], // currently selected rows for bulk ops
      members: [] as MemberItem[], // project members (for assignment)
      user: {} as MemberItem, // my role in this project
      isLoading: false, // list loading flag
      isProjectAdmin: false // quick flag to toggle admin-only UI
    }
  },

  /**
   * Nuxt fetch hook:
   * - fetches dataset list for current page/query
   * - fetches my role
   * - if admin, fetch member list (for assignment UI)
   */
  async fetch() {
    this.isLoading = true
    this.item = await this.$services.example.list(this.projectId, this.$route.query)
    this.user = await this.$repositories.member.fetchMyRole(this.projectId)
    if (this.user.isProjectAdmin) {
      this.members = await this.$repositories.member.list(this.projectId)
    }
    this.isLoading = false
  },

  computed: {
    // Pull current project (type, flags, etc.) from Vuex
    ...mapGetters('projects', ['project']),

    // Enable delete button when something is selected
    canDelete(): boolean {
      return this.selected.length > 0
    },

    // Convenience getter for project id from the route
    projectId(): string {
      return this.$route.params.id
    },

    /**
     * Column used to identify examples in the table:
     * - image/audio projects show "filename"
     * - text projects show "text"
     */
    itemKey(): string {
      if ((this as any).project.isImageProject || (this as any).project.isAudioProject) {
        return 'filename'
      } else {
        return 'text'
      }
    }
  },

  watch: {
    // Re-fetch the list when query params change (debounced to avoid spam requests)
    '$route.query': _.debounce(function (this: any) {
      this.$fetch()
    }, 1000)
  },

  // On create: compute a quick isProjectAdmin flag for conditional UI
  async created() {
    const member = await this.$repositories.member.fetchMyRole(this.projectId)
    this.isProjectAdmin = member.isProjectAdmin
  },

  methods: {
    // Delete selected rows, refresh list, close dialog, clear selection
    async remove() {
      await this.$services.example.bulkDelete(this.projectId, this.selected)
      this.$fetch()
      this.dialogDelete = false
      this.selected = []
    },

    // Delete ALL examples, refresh list, close dialog, clear selection
    async removeAll() {
      await this.$services.example.bulkDelete(this.projectId, [])
      this.$fetch()
      this.dialogDeleteAll = false
      this.selected = []
    },

    // Update query params (pagination, filters, etc.) via router
    updateQuery(query: object) {
      this.$router.push(query)
    },

    /**
     * Navigate to the labeling/annotation page.
     * getLinkToAnnotationPage() builds the correct route for the project's type.
     * We keep existing query state (e.g., which page) by passing it through.
     */
    movePage(query: object) {
      const link = getLinkToAnnotationPage(this.projectId, (this as any).project.projectType)
      this.updateQuery({
        path: this.localePath(link),
        query
      })
    },

    // Edit a single example (navigates to the edit page for that example)
    editItem(item: ExampleDTO) {
      this.$router.push(`dataset/${item.id}/edit`)
    },

    // Assign a single example to a user, then refresh list
    async assign(exampleId: number, userId: number) {
      await this.$repositories.assignment.assign(this.projectId, exampleId, userId)
      this.item = await this.$services.example.list(this.projectId, this.$route.query)
    },

    // Unassign by assignment id, then refresh list
    async unassign(assignmentId: string) {
      await this.$repositories.assignment.unassign(this.projectId, assignmentId)
      this.item = await this.$services.example.list(this.projectId, this.$route.query)
    },

    // After closing assignment modal, refresh list
    async assigned() {
      this.dialogAssignment = false
      this.item = await this.$services.example.list(this.projectId, this.$route.query)
    },

    // Reset all assignments, then refresh list
    async resetAssignment() {
      this.dialogReset = false
      await this.$repositories.assignment.reset(this.projectId)
      this.item = await this.$services.example.list(this.projectId, this.$route.query)
    }
  }
})
</script>

<style scoped>
/* Make dialogs wider so long names/details fit comfortably */
::v-deep .v-dialog {
  width: 800px;
}
</style>
