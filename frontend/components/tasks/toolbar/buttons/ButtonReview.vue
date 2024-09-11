<template>
  <v-tooltip bottom>
    <template #activator="{ on }">
      <v-btn
        v-shortkey.once="['enter']"
        icon
        v-on="on"
        @shortkey="startDownload()"
        @click="startDownload()"
      >
        <v-icon>
          {{ mdiFloppy }}
        </v-icon>
      </v-btn>
    </template>
    <span v-if="isReviewd">{{ $t('annotation.pushChanges') }}</span>
    <span v-else>{{ $t('annotation.pushChanges') }}</span>
  </v-tooltip>
</template>

<script lang="ts">
import Vue from 'vue'
import { mdiFloppy} from '@mdi/js'
import { fileFormatRules } from '@/rules/index'
import { Format } from '~/domain/models/download/format'

export default Vue.extend({

  middleware: ['check-auth', 'auth', 'setCurrentProject', 'isProjectAdmin'],

  validate({ params }) {
    return /^\d+$/.test(params.id)
  },

  props: {
    isReviewd: {
      type: Boolean,
      default: false,
      required: true
    },
    docId: {
      type: Number,
      required: true
    },
    requestSent: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      mdiFloppy,
      exportApproved: false,
      file: null,
      fileFormatRules,
      formats: [] as Format[],
      isProcessing: false,
      polling: null,
      selectedFormat: "JSONL",
      taskId: '',
      valid: false,
    }
  },

  computed: {
    projectId() {
      return this.$route.params.id
    },

    example(): string {
      const item = this.formats.find((item: Format) => item.name === "JSONL")
      return item!.example.trim()
    }
  },

  async created() {
    this.formats = await this.$repositories.downloadFormat.list(this.projectId)
  },

  methods: {
    handleReviewStatusUpdate(isReviewed: Boolean) {
      // Your custom actions based on the new review status
      if (isReviewed) {
        this.dataExportRequest();
      }
    },
    reset() {
      this.taskId = ''
      this.exportApproved = false
      this.selectedFormat = "JSONL"
      this.isProcessing = false
    },

    async dataExportRequest() {
      this.isProcessing = true
      const response = await this.$repositories.download.callGearboxAPI(
        this.projectId,
        this.docId,
        this.selectedFormat,
        this.exportApproved
      )
      if (response === 200){
        alert("Your data was sent successfully.")
      } else {
        alert("There was an error sending your data. Please try again")
      }
    },
    startDownload(){
      if (confirm("Are you sure you want to save? This will save changes to disk.")){
        this.dataExportRequest();
      }
    }
  },

})
</script>