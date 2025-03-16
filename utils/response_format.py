from flask import jsonify

class ResponseFormat:
    def __init__(
            self, 
            code, 
            message = "Success", 
            error = "",
            query = "", 
            page = "1", 
            data = [], 
            page_size = 0,
            total_data = 0
        ):
        self.code = code
        self.message = message
        self.error_message = error
        self.query = query
        self.page = page
        self.data = data
        self.page_size = page_size
        self.total_data = total_data

    def success(self):
        return jsonify({
            "code": self.code,
            "message": self.message,
            "query": self.query,
            "page": self.page,
            "data": self.data,
            "page_size": self.page_size,
            "total_data": self.total_data
        }), self.code

    def error(self):
        return jsonify({
            "code": self.code,
            "message": self.message,
            "data": [],
            "error": self.error_message
        }), self.code



