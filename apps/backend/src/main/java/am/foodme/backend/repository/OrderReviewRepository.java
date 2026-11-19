package am.foodme.backend.repository;

import am.foodme.backend.model.OrderReview;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface OrderReviewRepository extends JpaRepository<OrderReview, Long> {

    boolean existsByOrderId(Long orderId);

    long countByChefId(Long chefId);

    @Query("select coalesce(sum(r.rating), 0) from OrderReview r where r.chef.id = :chefId")
    long sumRatingByChefId(@Param("chefId") Long chefId);
}
