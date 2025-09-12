<template>
  <v-card>
    <!-- If the project supports multiple label kinds, show tabs to switch -->
    <v-tabs v-if="hasMultiType" v-model="tab">
      <template v-if="isIntentDetectionAndSlotFilling">
        <v-tab class="text-capitalize">Category</v-tab>
        <v-tab class="text-capitalize">Span</v-tab>
      </template>
      <template v-else>
        <v-tab class="text-capitalize">Span</v-tab>
        <v-tab class="text-capitalize">Relation</v-tab>
      </template>
    </v-tabs>

    <v-card-title>
      <!-- Action menu: create/upload/download for the active label type -->
      <action-menu
        :add-only="canOnlyAdd"
        @create="$router.push('labels/add?type=' + labelType)"
        @upload="$router.push('labels/import?type=' + labelType)"
        @download="download"
      />

      <!-- Bulk delete button (disabled until something is selected) -->
      <v-btn
        v-if="!canOnlyAdd"
        class="text-capitalize ms-2"
        :disabled="!canDelete"
        outlined
        @click.stop="dialogDelete = true"
      >
        {{ $t('generic.delete') }}
      </v-btn>

      <!-- Confirm delete dialog -->
      <v-dialog v-model="dialogDelete">
        <form-delete :selected="selected" @cancel="dialogDelete = false" @remove="remove" />
      </v-dialog>
    </v-card-title>

    <!-- Label list table for the current tab/type -->
    <label-list
      v-model="selected"
      :items="items"
      :is-loading="isLoading"
      :disable-edit="canOnlyAdd"
      @edit="editItem"
    />
  </v-card>
</template>

<script lang="ts">
import { mapGetters } from 'vuex'
import Vue from 'vue'
import ActionMenu from '@/components/label/ActionMenu.vue'
import FormDelete from '@/components/label/FormDelete.vue'
import LabelList from '@/components/label/LabelList.vue'
import { LabelDTO } from '~/services/application/label/labelData'
import { MemberItem } from '~/domain/models/member/member'

export default Vue.extend({
  components: {
    ActionMenu,
    FormDelete,
    LabelList
  },

  // Use the project layout (sidebar/breadcrumbs)
  layout: 'project',

  // Must be authed and have current project
  middleware: ['check-auth', 'auth', 'setCurrentProject'],

  /**
   * Route guard:
   * - :id must be numeric
   * - user must either be project admin OR project allows members to create label types
   * - project must allow label definition at all (canDefineLabel)
   */
  validate({ params, app, store }) {
    if (/^\d+$/.test(params.id)) {
      const project = store.getters['projects/project']
      if (!project.canDefineLabel) {
        return false
      }
      // Fetch my role to decide if I can proceed
      return app.$repositories.member.fetchMyRole(params.id).then((member: MemberItem) => {
        if (member.isProjectAdmin) {
          return true
        }
        return project.allowMemberToCreateLabelType
      })
    }
    return false
  },

  data() {
    return {
      dialogDelete: false, // controls delete dialog open/close
      items: [] as LabelDTO[], // rows shown in the label list
      selected: [] as LabelDTO[], // rows selected for bulk delete
      isLoading: false, // table loading state
      tab: 0, // active tab index (0 or 1)
      member: {} as MemberItem // my role in this project
    }
  },

  computed: {
    // Pull the current project from the store
    ...mapGetters('projects', ['project']),

    /**
     * If I’m not an admin, check whether members are allowed to add labels.
     * This drives UI that hides edit/delete and shows only "add".
     */
    canOnlyAdd(): boolean {
      if (this.member.isProjectAdmin) {
        return false
      }
      return (this as any).project.allowMemberToCreateLabelType
    },

    // Enable bulk delete button when any row is selected
    canDelete(): boolean {
      return this.selected.length > 0
    },

    // Convenience getter for the numeric project id in the route
    projectId(): string {
      return this.$route.params.id
    },

    /**
     * Whether the project has multiple label types (tabs).
     * For IDSF (intent + slot), or projects that use relations, we show tabs.
     */
    hasMultiType(): boolean {
      if ('projectType' in (this as any).project) {
        return this.isIntentDetectionAndSlotFilling || !!(this as any).project.useRelation
      } else {
        return false
      }
    },

    // Helpful boolean to branch UI for IDSF projects
    isIntentDetectionAndSlotFilling(): boolean {
      return (this as any).project.projectType === 'IntentDetectionAndSlotFilling'
    },

    /**
     * Active label type string used by actions and routes.
     * Mapping is driven by the current tab.
     * Note: the non-null assertion on `tab!` reflects that v-tabs always sets a numeric index.
     */
    labelType(): string {
      if (this.hasMultiType) {
        if (this.isIntentDetectionAndSlotFilling) {
          return ['category', 'span'][this.tab!]
        } else {
          return ['span', 'relation'][this.tab!]
        }
      } else if ((this as any).project.canDefineCategory) {
        return 'category'
      } else {
        return 'span'
      }
    },

    /**
     * Service instance to call for list / delete / export depending on the active type.
     * - category  => this.$services.categoryType
     * - span      => this.$services.spanType
     * - relation  => this.$services.relationType
     */
    service(): any {
      if (!('projectType' in (this as any).project)) {
        return
      }
      if (this.hasMultiType) {
        if (this.isIntentDetectionAndSlotFilling) {
          return [this.$services.categoryType, this.$services.spanType][this.tab!]
        } else {
          return [this.$services.spanType, this.$services.relationType][this.tab!]
        }
      } else if ((this as any).project.canDefineCategory) {
        return this.$services.categoryType
      } else {
        return this.$services.spanType
      }
    }
  },

  watch: {
    // When the tab changes, reload the list for the new type
    tab() {
      this.list()
    }
  },

  // On page load, fetch my role and load the current list
  async created() {
    this.member = await this.$repositories.member.fetchMyRole(this.projectId)
    await this.list()
  },

  methods: {
    // Fetch labels for the active type and show a loading state during the request
    async list() {
      this.isLoading = true
      this.items = await this.service.list(this.projectId)
      this.isLoading = false
    },

    // Bulk delete selected rows, then refresh the list and reset selection/dialog
    async remove() {
      await this.service.bulkDelete(this.projectId, this.selected)
      this.list()
      this.dialogDelete = false
      this.selected = []
    },

    // Export labels for the active type
    async download() {
      await this.service.export(this.projectId)
    },

    // Navigate to the edit page for a single label row (preserving active type)
    editItem(item: LabelDTO) {
      this.$router.push(`labels/${item.id}/edit?type=${this.labelType}`)
    }
  }
})
</script>

<style scoped>
/* Wider delete dialog so long names fit comfortably */
::v-deep .v-dialog {
  width: 800px;
}
</style>
