package am.foodme.backend.service;

import am.foodme.backend.exceptionHandler.NotFoundException;
import am.foodme.backend.model.Dish;
import am.foodme.backend.repository.DishRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class DishServiceTest {

    @Mock
    private DishRepository dishRepository;

    @InjectMocks
    private DishService dishService;

    @Test
    void getDishById_existingId_returnsDish() {
        Dish dish = new Dish();
        when(dishRepository.findById(1L)).thenReturn(Optional.of(dish));

        assertThat(dishService.getDishById(1L)).isSameAs(dish);
    }

    @Test
    void getDishById_missingId_throwsNotFound() {
        when(dishRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> dishService.getDishById(99L))
                .isInstanceOf(NotFoundException.class)
                .hasMessage("Dish 99 not found");
    }

    @Test
    void getActiveDishesForChef_queriesActiveStatusWithRequestedPage() {
        Page<Dish> page = new PageImpl<>(List.of(new Dish()));
        when(dishRepository.findByChefIdAndStatus(1L, "ACTIVE", PageRequest.of(2, 10))).thenReturn(page);

        assertThat(dishService.getActiveDishesForChef(1L, 2, 10)).isSameAs(page);
    }
}
