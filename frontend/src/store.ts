import { defineStore } from 'pinia'
import { api, type Device, type Health, type Service } from './api'

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    devices: [] as Device[],
    services: [] as Service[],
    loading: false,
    error: ''
  }),
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        const data = await api.dashboard()
        this.devices = data.devices
        this.services = data.services
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载失败'
      } finally {
        this.loading = false
      }
    },
    replaceService(service: Service) {
      const index = this.services.findIndex((item) => item.id === service.id)
      if (index >= 0) this.services[index] = service
    },
    async toggleFavorite(service: Service) {
      this.replaceService(await api.favorite(service.id, !service.favorite))
      await this.load()
    },
    async check(service: Service) {
      const health: Health = await api.check(service.id)
      service.health = health
      await this.load()
    }
  }
})

