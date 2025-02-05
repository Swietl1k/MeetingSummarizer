export class ApiClient {

    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }

    async makeRequest(config) {
        try {
            const client = this.#createClient();
            const response = await client.request(config);
            return response.data;
        } catch(error) {
            this.handleError(error);
        }
    }

    #createClient() {
        const baseConfig = {
            baseURL: this.baseUrl,
        };

        return axios.create(baseConfig);
    }

    handleError(error) {
        throw error;
    }

}
