<template>
  <v-card>
    <!-- Page title -->
    <v-card-title>
      {{ $t('dataset.importDataTitle') }}
    </v-card-title>

    <v-card-text>
      <!-- Full-page spinner while an import task is running -->
      <v-overlay :value="isImporting">
        <v-progress-circular indeterminate size="64" />
      </v-overlay>

      <!-- Choose file format (e.g., JSONL, CSV, etc.) -->
      <v-select
        v-model="selected"
        :items="catalog"
        item-text="displayName"
        label="File format"
        outlined
      />

      <!-- Extra options for the selected format (e.g., delimiter) -->
      <v-form v-model="valid">
        <!-- Text inputs (simple strings) -->
        <v-text-field
          v-for="(item, key) in textFields"
          :key="key"
          v-model="option[key]"
          :label="item.title"
          :rules="requiredRules"
          outlined
        />
        <!-- Select inputs (enums) -->
        <v-select
          v-for="(val, key) in selectFields"
          :key="key"
          v-model="option[key]"
          :items="val.enum"
          :label="val.title"
          outlined
        >
          <template #selection="{ item }">
            {{ toVisualize(item) }}
          </template>
          <template #item="{ item }">
            {{ toVisualize(item) }}
          </template>
        </v-select>
      </v-form>

      <!-- Example block for the chosen format -->
      <v-sheet
        v-if="selected"
        :dark="!$vuetify.theme.dark"
        :light="$vuetify.theme.dark"
        class="mb-5 pa-5"
      >
        <pre>{{ example }}</pre>
      </v-sheet>

      <!-- Pretty view specifically for Relation JSONL (just a helper preview) -->
      <div v-if="selected === 'JSONL(Relation)'">
        <p class="body-1">For readability, the above format can be displayed as follows:</p>
        <v-sheet :dark="!$vuetify.theme.dark" :light="$vuetify.theme.dark" class="mb-5 pa-5">
          <pre>{{ JSON.stringify(JSON.parse(example.replaceAll("'", '"')), null, 4) }}</pre>
        </v-sheet>
      </div>

      <!-- Only show the JSONL tip when the selected format is JSONL (Maybe add others as needed). -->
      <v-alert
        v-if="selected && /jsonl/i.test(String(selected.value || selected))"
        type="info"
        outlined
        dense
        class="mb-4"
      >
        Tip: For <strong>JSONL</strong>, use one JSON object per line. Pretty-printed JSON will
        fail.
      </v-alert>

      <!-- File upload area (FilePond). For “*” accept-types, allow any file. -->
      <file-pond
        v-if="selected && acceptedFileTypes !== '*'"
        ref="pond"
        chunk-uploads="true"
        label-idle="Drop files here..."
        :allow-multiple="true"
        :accepted-file-types="acceptedFileTypes"
        :server="server"
        :files="myFiles"
        @processfile="handleFilePondProcessFile"
        @removefile="handleFilePondRemoveFile"
      />
      <file-pond
        v-if="selected && acceptedFileTypes === '*'"
        ref="pond"
        chunk-uploads="true"
        label-idle="Drop files here..."
        :allow-multiple="true"
        :server="server"
        :files="myFiles"
        @processfile="handleFilePondProcessFile"
        @removefile="handleFilePondRemoveFile"
      />

      <!-- Error table after a finished task (we fill this from polling results) -->
      <div v-if="errors.length > 0" class="mt-4">
        <v-alert type="error" border="left" colored-border elevation="2">
          {{ errors.length }} error(s) found during dataset import. Please check the table below:
        </v-alert>
        <v-data-table
          :headers="headers"
          :items="errors"
          class="elevation-1"
          dense
          disable-pagination
        />
      </div>
    </v-card-text>

    <!-- Kick off the import task -->
    <v-card-actions>
      <v-btn class="text-capitalize ms-2 primary" :disabled="isDisabled" @click="importDataset">
        {{ $t('generic.import') }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import FilePondPluginFileValidateType from 'filepond-plugin-file-validate-type'
import 'filepond/dist/filepond.min.css'
import Cookies from 'js-cookie'
import vueFilePond from 'vue-filepond'

const FilePond = vueFilePond(FilePondPluginFileValidateType)

export default {
  components: {
    FilePond
  },

  // Use project layout
  layout: 'project',

  // Must be signed in, in a project, and have admin rights to import
  middleware: ['check-auth', 'auth', 'setCurrentProject', 'isProjectAdmin'],

  // Validate the route param is a numeric project id
  validate({ params }) {
    return /^\d+$/.test(params.id)
  },

  data() {
    return {
      // Format catalog from the backend (e.g., JSONL, CSV, etc.)
      catalog: [],
      // Selected catalog item (string or object depending on API)
      selected: null,

      // Files staged in FilePond (UI). `uploadedFiles` is the server-side result.
      myFiles: [],
      uploadedFiles: [],

      // Per-format options (bound to dynamic form above)
      option: { column_data: '', column_label: '', delimiter: '' },

      // Async task tracking
      taskId: null, // Celery task id returned by the API
      polling: null, // setInterval handle
      _pollingBusy: false, // guard: only one poll at a time
      polledDone: false, // guard: handle ready block once
      pollTimerMs: 1000, // poll every second

      // UI state
      valid: false, // form validity from <v-form>
      isImporting: false, // overlay spinner toggle

      // Error table data
      errors: [],
      headers: [
        { text: 'Filename', value: 'filename' },
        { text: 'Line', value: 'line' },
        { text: 'Message', value: 'message' }
      ],

      // Simple required rule for dynamic text fields
      requiredRules: [(v) => !!v || 'Field value is required'],

      // FilePond server config (points at backend filepond endpoints)
      server: {
        url: '/v1/fp',
        headers: {
          'X-CSRFToken': Cookies.get('csrftoken')
        },
        process: { url: '/process/', method: 'POST' },
        patch: '/patch/',
        revert: '/revert/',
        restore: '/restore/',
        load: '/load/',
        fetch: '/fetch/'
      }
    }
  },

  computed: {
    // Disable the import button unless we have files, a valid form, and no running task
    isDisabled() {
      return this.uploadedFiles.length === 0 || this.taskId !== null || !this.valid
    },

    // Resolve properties for the selected format (drives the dynamic form)
    properties() {
      const item = this.catalog.find((item) => item.displayName === this.selected)
      return item ? item.properties : {}
    },

    // Split properties into text inputs (no enum)
    textFields() {
      const asArray = Object.entries(this.properties)
      const textFields = asArray.filter(([_, value]) => !('enum' in value))
      return Object.fromEntries(textFields)
    },

    // Split properties into select inputs (has enum)
    selectFields() {
      const asArray = Object.entries(this.properties)
      const textFields = asArray.filter(([_, value]) => 'enum' in value)
      return Object.fromEntries(textFields)
    },

    // Accepted file types for FilePond (e.g., ['text/csv'] or '*')
    acceptedFileTypes() {
      const item = this.catalog.find((item) => item.displayName === this.selected)
      return item ? item.acceptTypes : ''
    },

    // Example payload for the selected format (with placeholders swapped if needed)
    example() {
      const item = this.catalog.find((item) => item.displayName === this.selected)
      if (!item) return ''
      const column_data = 'column_data'
      const column_label = 'column_label'
      if (column_data in this.option && column_label in this.option) {
        return item.example
          .replaceAll(column_data, this.option[column_data])
          .replaceAll(column_label, this.option[column_label])
          .trim()
      }
      return item.example.trim()
    }
  },

  watch: {
    // When the format changes:
    // - reset option defaults for this format
    // - clear uploaded files (both UI + server)
    // - clear any previous errors
    selected() {
      const item = this.catalog.find((item) => item.displayName === this.selected)
      for (const [key, value] of Object.entries(item.properties)) {
        this.option[key] = value.default
      }
      this.myFiles = []
      for (const file of this.uploadedFiles) {
        this.$repositories.parse.revert(file.serverId)
      }
      this.uploadedFiles = []
      this.errors = []
    }
  },

  async created() {
    // Load supported import formats for this project from the backend
    this.catalog = await this.$repositories.catalog.list(this.$route.params.id)
    // Start polling loop (it will do nothing until taskId is set)
    this.pollData()
  },

  beforeDestroy() {
    // Make sure we stop polling on navigation away
    clearInterval(this.polling)
  },

  methods: {
    // FilePond: a file was successfully uploaded to temp storage
    handleFilePondProcessFile(err, file) {
      if (err) {
        // Mark the error as handled to satisfy the rule and show feedback
        console.error('FilePond process error:', err)
        this.errors = [
          {
            filename: file?.filename || file?.name || 'Upload',
            line: '-',
            message: err?.message || String(err)
          }
        ]
        return
      }

      this.uploadedFiles.push(file)
      this.$nextTick()
    },

    // FilePond: a file was removed from the pond
    handleFilePondRemoveFile(err, file) {
      if (err) {
        console.error('FilePond remove error:', err)
        return
      }

      const index = this.uploadedFiles.findIndex((item) => item.id === file.id)
      if (index > -1) {
        this.uploadedFiles.splice(index, 1)
        this.$nextTick()
      }
    },

    /**
     * Start the import task on the backend.
     * The backend returns a Celery task id; we keep polling it until it’s done.
     * Contract:
     *   - success => result.error is an empty array => redirect to dataset page
     *   - failure => result.error contains rows to show in the table
     */
    async importDataset() {
      // New attempt => clear previous state
      this.errors = []
      this.taskId = null
      this.isImporting = true
      this.polledDone = false

      try {
        // Resolve the selected format entry from the catalog
        const item = this.catalog.find((item) => item.displayName === this.selected)

        // Ask backend to analyze/import the uploaded files
        // (returns a task id we’ll poll below)
        this.taskId = await this.$repositories.parse.analyze(
          this.$route.params.id, // project id
          item.name, // backend format name
          item.taskId, // task type
          this.uploadedFiles.map((item) => item.serverId), // temp upload ids
          this.option // extra parse options
        )
      } catch (e) {
        // Immediate failure (network, 4xx/5xx before task creation)
        this.isImporting = false

        const errorData = e?.response?.data

        // Array of errors (structured)
        if (Array.isArray(errorData?.detail)) {
          this.errors = errorData.detail.map((d) => ({
            filename: d.filename || 'Upload error',
            line: d.line || '-',
            message: d.msg || d.message || 'Issue found.'
          }))
        } else {
          // Single error (string or object)
          const backendError = errorData?.detail || errorData?.error || e.message
          this.errors = [
            {
              filename: 'Upload error',
              line: '-',
              message: backendError || 'Upload failed. Please check your file format or try again.'
            }
          ]
        }
      }
    },

    /**
     * Poll Celery task status until it is ready.
     * - On success (no errors): clear selections and navigate back to dataset list.
     * - On failure: show a normalized, de-duplicated errors table.
     */
    pollData() {
      this.polling = setInterval(async () => {
        // Nothing to do until a task id exists
        if (!this.taskId || this._pollingBusy) return
        this._pollingBusy = true

        try {
          // Ask backend for current task status
          const res = await this.$repositories.taskStatus.get(this.taskId)
          const result = (res && res.result) || {}
          const errors = Array.isArray(result.error) ? result.error : []

          // Only handle a finished task
          if (res && res.ready) {
            // Stop polling (run only once per task)
            if (this.polling) {
              clearInterval(this.polling)
              this.polling = null
            }
            if (this.polledDone) return
            this.polledDone = true

            // Reset task UI state
            this.taskId = null
            this.isImporting = false

            // SUCCESS: empty error array means the import worked
            if (errors.length === 0) {
              this.myFiles = []
              this.uploadedFiles = []
              const projectId = this.$route.params.id
              // Use replace() so "Back" doesn't return to the import page
              this.$router.replace(`/projects/${projectId}/dataset`)
              return
            }

            // FAILURE: normalize the task's error rows for the table
            const rows = errors.map((e) => ({
              filename: (e && (e.filename || e.file)) || 'Import',
              line: (e && (e.line ?? e.row)) ?? '-',
              message:
                typeof e === 'string' ? e : (e && (e.message || e.detail)) || JSON.stringify(e)
            }))

            // Remove duplicates so the table is clean (sometimes backends repeat)
            const seen = new Set()
            this.errors = rows.filter((r) => {
              const k = `${r.filename}|${r.line}|${(r.message || '').trim()}`
              if (seen.has(k)) return false
              seen.add(k)
              return true
            })

            return
          }
        } catch (err) {
          // Network/HTTP errors during polling => show a readable message
          this.errors = [
            {
              filename: 'Polling error',
              line: '-',
              message:
                (err && err.response && (err.response.data?.detail || err.response.data?.error)) ||
                err?.message ||
                'Unexpected error during import polling.'
            }
          ]
          this.isImporting = false
          this.taskId = null

          // Stop polling on hard failure
          if (this.polling) {
            clearInterval(this.polling)
            this.polling = null
          }
        } finally {
          this._pollingBusy = false
        }
      }, this.pollTimerMs)
    },

    // Display-friendly labels for special characters in selects
    toVisualize(text) {
      if (text === '\t') {
        return 'Tab'
      } else if (text === ' ') {
        return 'Space'
      } else if (text === '') {
        return 'None'
      } else {
        return text
      }
    }
  }
}
</script>
