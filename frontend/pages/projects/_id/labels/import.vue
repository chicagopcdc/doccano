<template>
  <div>
    <!-- Shows an alert only when there is an error -->
    <div v-if="errorMessage" class="alert alert-danger">
      {{ errorMessage }}
    </div>

    <!--
      Re-usable upload form component for label imports.
      We pass down:
        - errorMessage (so the child can show inline validation if needed)
        - loading (so the child can disable buttons/spinners)
      And we listen for:
        - @clear  => parent clears error banner
        - @upload => parent runs the actual upload logic
    -->
    <form-import
      :error-message="errorMessage"
      :loading="loading"
      @clear="clearErrorMessage"
      @upload="upload"
    />
  </div>
</template>

<script lang="ts">
import Vue from 'vue'
import FormImport from '@/components/label/FormImport.vue'

export default Vue.extend({
  components: {
    FormImport
  },

  // Use the "project" layout shell (breadcrumbs, sidebar, etc.)
  layout: 'project',

  // Gatekeeping: must be authed, have a current project, and be a project admin
  middleware: ['check-auth', 'auth', 'setCurrentProject', 'isProjectAdmin'],

  /**
   * Route-level validation:
   * - only allow ?type=category|span|relation
   * - :id must be numeric and the current project must allow label definition
   */
  validate({ params, query, store }) {
    if (!['category', 'span', 'relation'].includes(query.type as string)) {
      return false
    }
    if (/^\d+$/.test(params.id)) {
      const project = store.getters['projects/project']
      return project.canDefineLabel
    }
    return false
  },

  data() {
    return {
      // Controls button/spinner state in the child form
      loading: false as boolean,
      // Text shown in the red alert at the top (empty string hides it)
      errorMessage: '' as string
    }
  },

  computed: {
    // Convenience accessor for the :id route param
    projectId(): string {
      return this.$route.params.id
    },

    /**
     * Picks the correct API service for this label type.
     * - category  => classification label types
     * - span      => sequence labeling (spans)
     * - relation  => relation types
     */
    service(): any {
      const type = this.$route.query.type
      if (type === 'category') {
        return this.$services.categoryType
      } else if (type === 'span') {
        return this.$services.spanType
      } else {
        return this.$services.relationType
      }
    }
  },

  methods: {
    /**
     * Upload a labels file for the current project.
     * UX goals:
     *  - show a spinner while uploading
     *  - on success: go back to the Labels list
     *  - on failure: show a helpful error message
     *
     * Defensively inspect resp.status in case a response object was returned.
     */
    async upload(file: File) {
      try {
        // Clear any previous error and show loading state
        this.clearErrorMessage()
        this.loading = true

        // Send the file to the backend via the chosen label service
        const resp = await this.service.upload(this.projectId, file)

        // Treat any 2xx response as success (some adapters may not throw on non-2xx)
        // Default to 201 (Created) if a status did not attach.
        const status = resp?.status ?? 201
        if (status >= 200 && status < 300) {
          // Success: navigate back to the Labels page for this project.
          // Use replace() so the browser Back button doesn't return to the import form.
          this.$router.replace(`/projects/${this.projectId}/labels`)
          return
        }

        // Non-2xx without a thrown error: show a simple message.
        this.errorMessage = 'Upload failed. Please check label format or contents.'
      } catch (e: any) {
        // A request error was thrown. Try to extract a useful message.
        // APIs may return { error: [...] } or { detail: '...' } or a plain array.
        const data = e?.response?.data
        const arr = Array.isArray(data?.error) ? data.error : Array.isArray(data) ? data : []
        if (arr.length) {
          // Collect a few messages so the user sees something concise.
          type ErrLike = { message?: string; detail?: string } | string
          const msgs = (arr as ErrLike[])
            .map((x) => (typeof x === 'string' ? x : x.message ?? x.detail ?? String(x)))
            .slice(0, 3)

          this.errorMessage = msgs.join(' | ')
        } else {
          // Fallback: DRF detail => generic error string => thrown message => generic fallback
          this.errorMessage =
            data?.detail ||
            data?.error ||
            e?.message ||
            'Upload failed. Please check label format or contents.'
        }
      } finally {
        // Stop the spinner (success or failure)
        this.loading = false
      }
    },

    /**
     * Clears the displayed error message.
     */
    clearErrorMessage() {
      this.errorMessage = ''
    }
  }
})
</script>
