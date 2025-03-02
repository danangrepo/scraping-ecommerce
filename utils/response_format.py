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
            total = 0
        ):
        self.code = code
        self.message = message
        self.error_message = error
        self.query = query
        self.page = page
        self.data = data
        self.total = total

    def success(self):
        return jsonify({
            "code": self.code,
            "message": self.message,
            "query": self.query,
            "page": self.page,
            "data": self.data,
            "total": self.total
        }), self.code

    def error(self):
        return jsonify({
            "code": self.code,
            "message": self.message,
            "data": [],
            "error": self.error_message
        }), self.code



