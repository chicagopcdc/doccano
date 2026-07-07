import ApiService from '@/services/api.service'

export class APIDownloadRepository {
  constructor(private readonly request = ApiService) {}

  async prepare(
    projectId: string,
    format: string,
    exportApproved: boolean,
    ids?: number[]
  ): Promise<string> {
    const url = `/projects/${projectId}/download`
    const data: { format: string; exportApproved: boolean; ids?: number[] } = {
      format,
      exportApproved
    }
    if (ids && ids.length > 0) {
      data.ids = ids
    }
    const response = await this.request.post(url, data)
    return response.data.task_id
  }

  async download(projectId: string, taskId: string): Promise<void> {
    const url = `/projects/${projectId}/download?taskId=${taskId}`
    const config = {
      responseType: 'blob'
    }
    const response = await this.request.get(url, config)
    const downloadUrl = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = downloadUrl
    link.setAttribute('download', `${taskId}.zip`)
    document.body.appendChild(link)
    link.click()
  }
}
