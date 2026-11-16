package am.foodme.backend.service;

import am.foodme.backend.dto.CreateOrderReviewRequestDto;
import am.foodme.backend.dto.OrderReviewDto;
import am.foodme.backend.exceptionHandler.BadRequestException;
import am.foodme.backend.exceptionHandler.NotFoundException;
import am.foodme.backend.model.Chef;
import am.foodme.backend.model.Customer;
import am.foodme.backend.model.Order;
import am.foodme.backend.model.OrderReview;
import am.foodme.backend.repository.ChefRepository;
import am.foodme.backend.repository.CustomerRepository;
import am.foodme.backend.repository.OrderRepository;
import am.foodme.backend.repository.OrderReviewRepository;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;

/** SCRUM-6 Order Ratings: customers rate their delivered orders; chef ratings follow the reviews. */
@Service
public class OrderReviewService {

    public static final String ONLY_DELIVERED_MESSAGE = "Only delivered orders can be reviewed.";
    public static final String ALREADY_REVIEWED_MESSAGE = "Order already reviewed.";

    private final OrderReviewRepository orderReviewRepository;
    private final OrderRepository orderRepository;
    private final CustomerRepository customerRepository;
    private final ChefRepository chefRepository;
    private final MeterRegistry meterRegistry;

    public OrderReviewService(OrderReviewRepository orderReviewRepository, OrderRepository orderRepository,
                              CustomerRepository customerRepository, ChefRepository chefRepository,
                              MeterRegistry meterRegistry) {
        this.orderReviewRepository = orderReviewRepository;
        this.orderRepository = orderRepository;
        this.customerRepository = customerRepository;
        this.chefRepository = chefRepository;
        this.meterRegistry = meterRegistry;
    }

    @Transactional
    public OrderReviewDto createReview(String orderNumber, CreateOrderReviewRequestDto request, String customerEmail) {
        Customer customer = customerRepository.findByEmail(customerEmail == null ? "" : customerEmail.trim().toLowerCase())
                .orElseThrow(() -> new NotFoundException("Customer not found"));

        // R7: someone else's order looks exactly like a missing one.
        Order order = orderRepository.findByNumber(orderNumber)
                .filter(o -> o.getCustomer() != null && o.getCustomer().getId().equals(customer.getId()))
                .orElseThrow(() -> new NotFoundException("Order " + orderNumber + " not found"));

        if (!"DELIVERED".equals(order.getStatus())) {
            throw new BadRequestException(ONLY_DELIVERED_MESSAGE);
        }
        if (orderReviewRepository.existsByOrderId(order.getId())) {
            throw new BadRequestException(ALREADY_REVIEWED_MESSAGE);
        }

        // Lock the chef first so two reviews for the same chef recalculate its rating one after the other.
        Chef chef = chefRepository.findByIdForUpdate(order.getChef().getId())
                .orElseThrow(() -> new NotFoundException("Chef " + order.getChef().getId() + " not found"));

        OrderReview review = new OrderReview();
        review.setOrder(order);
        review.setCustomer(customer);
        review.setChef(chef);
        review.setRating(request.getRating().intValueExact());
        review.setComment(normalizeComment(request.getComment()));
        review.setCreatedAt(LocalDateTime.now());

        OrderReview saved;
        try {
            saved = orderReviewRepository.saveAndFlush(review);
        } catch (DataIntegrityViolationException e) {
            // A concurrent request for the same order won the unique(order_id) race.
            throw new BadRequestException(ALREADY_REVIEWED_MESSAGE);
        }
        order.setReview(saved);

        chef.setRating(averageRating(chef.getId()));
        chefRepository.save(chef);

        meterRegistry.counter("foodme.reviews", "rating", String.valueOf(saved.getRating())).increment();

        return OrderReviewDto.mapEntityToDto(saved);
    }

    /** R10/R11: the average of all the chef's reviews, rounded half-up to one decimal place. */
    private Double averageRating(Long chefId) {
        long count = orderReviewRepository.countByChefId(chefId);
        if (count == 0) {
            return null;
        }
        long sum = orderReviewRepository.sumRatingByChefId(chefId);
        return BigDecimal.valueOf(sum)
                .divide(BigDecimal.valueOf(count), 1, RoundingMode.HALF_UP)
                .doubleValue();
    }

    private static String normalizeComment(String comment) {
        if (comment == null) {
            return null;
        }
        String trimmed = comment.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
