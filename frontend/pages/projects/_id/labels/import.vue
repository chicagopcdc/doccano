<template>
  <div>
    <!-- Error alert (only shows when errorMessage is set) -->
    <div v-if="errorMessage" class="alert alert-danger">
      {{ errorMessage }}
    </div>

    <!-- Your existing import form -->
    <form-import :error-message="errorMessage" @clear="clearErrorMessage" @upload="upload" />
  </div>
</template>


<script lang="ts">
import Vue from 'vue'
import FormImport from '~/components/label/FormImport.vue'

export default Vue.extend({
  components: {
    FormImport
  },

  layout: 'project',

  middleware: ['check-auth', 'auth', 'setCurrentProject', 'isProjectAdmin'],

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
      loading: false as boolean,
      errorMessage: '' as string
    }
  },

  computed: {
    projectId(): string {
      return this.$route.params.id
    },

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
     * Uploads a dataset file to the backend for the current project.
     * Handles user feedback for common failure modes like long label text.
     */
    async upload(file: File) {
      try {
        // Always clear previous errors before new upload
        this.clearErrorMessage()

        // Optional: set loading state if you're showing a spinner
        this.loading = true

        // Start uploading the file using the service layer
        await this.service.upload(this.projectId, file)

        // On success, redirect user to the project's label page
        this.$router.push(`/projects/${this.projectId}/labels`)
      } catch (e: any) {
        // Extract backend error message from known response formats
        const backendError =
          e?.response?.data?.detail || // Django REST Framework error detail
          e?.response?.data?.error || // Generic error key if present
          e?.message // Axios / JS error message fallback

        // Set the error message shown in the frontend
        this.errorMessage =
          backendError || 'Upload failed. Please check label length or file format.'
      } finally {
        // Always stop spinner even if upload fails
        this.loading = false
      }
    },

    /**
     * Clears the displayed error message.
     * Can be triggered by retry logic or close buttons in the UI.
     */
    clearErrorMessage() {
      this.errorMessage = ''
    }
  }
})
</script>
