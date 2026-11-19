package am.foodme.backend.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Digits;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.math.BigDecimal;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class CreateOrderReviewRequestDto {
    public static final String RATING_MESSAGE = "Rating must be a whole number from 1 to 5";
    public static final String COMMENT_MESSAGE = "Comment must be at most 1000 characters";

    // BigDecimal, not Integer: Jackson would silently truncate 4.5 to 4 for an int field,
    // and R2 says fractional ratings must be refused.
    @NotNull(message = RATING_MESSAGE)
    @DecimalMin(value = "1", message = RATING_MESSAGE)
    @DecimalMax(value = "5", message = RATING_MESSAGE)
    @Digits(integer = 1, fraction = 0, message = RATING_MESSAGE)
    private BigDecimal rating;

    @Size(max = 1000, message = COMMENT_MESSAGE)
    private String comment;
}
