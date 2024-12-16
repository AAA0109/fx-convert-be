class ForwardPointProvider:

    def __get_multiplier(self, side: str) -> int:
        return -1 if side == "Sell" else 1

    def determine_fwd_points_sign(self, fwd_point:float, side:str) -> float:
        if fwd_point is None:
            return 0.0
        return self.__get_multiplier(side=side) * fwd_point

    def to_fwd_point_expression(self, fwd_point:float, rate:float) -> float:
        if rate == None:
            return f"0.0 / 0.00%"
        return f"{round(fwd_point, 4)} / {round(fwd_point/rate * 100, 2)}%"
